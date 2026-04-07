import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session, load_only
from sqlalchemy.exc import IntegrityError
from sqlalchemy import cast, func, select, text, update
from sqlalchemy.types import BigInteger
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

import logging

from .database import Base, engine, get_db, ensure_schema_columns
from . import models
from .etl_matcher import ETLMatcher
from .auth_core import create_access_token, verify_password, hash_password
from . import schemas
from .deps import get_current_user, get_current_user_dashboard, verify_sync_api_key

logger = logging.getLogger(__name__)

_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
ALLOWED_ORIGINS = [o.strip() for o in _origins.split(",") if o.strip()]

app = FastAPI(title="SwissTools Pos — API dashboard", version="1.3")


@app.on_event("startup")
def _on_startup():
    """Crea tablas si no existen. No mata el proceso si la DB tarda en responder."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("create_all OK — tablas base verificadas")
    except Exception as exc:
        logger.error("create_all falló (se reintentará en la primera petición): %s", exc)
    try:
        ensure_schema_columns()
        logger.info("ensure_schema_columns OK — columnas sync/dashboard al día")
    except Exception:
        logger.exception(
            "ensure_schema_columns falló al arranque; el próximo POST /sync/upload reintentará "
            "(o revisa permisos ALTER en la DB y migraciones Supabase)."
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _user_me(db: Session, user: models.Usuario) -> schemas.UserMe:
    links = (
        db.query(models.UsuarioSucursal, models.Sucursal)
        .join(models.Sucursal, models.Sucursal.id == models.UsuarioSucursal.sucursal_id)
        .filter(models.UsuarioSucursal.usuario_id == user.id)
        .all()
    )
    sucursales = [
        schemas.SucursalBrief(id=s.id, nombre=s.nombre, rol=link.rol)
        for link, s in links
    ]
    return schemas.UserMe(
        id=user.id,
        email=user.email,
        nombre=user.nombre,
        is_admin=user.is_admin,
        portal_admin=user.portal_admin,
        sucursales=sucursales,
    )


def _require_admin(user: models.Usuario) -> None:
    # Swiss Tools Dashboard Admon: acceso solo para usuarios con `portal_admin`.
    if not user.portal_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado (admin requerido)")


def _require_maintenance_access(user: models.Usuario) -> None:
    """Borrado de ventas importadas: portal admin o admin del dashboard legado."""
    if not (user.portal_admin or user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para mantenimiento de datos sincronizados",
        )


def _purge_ventas_importadas(
    db: Session,
    sucursal: models.Sucursal,
    *,
    completo: bool,
    fecha_desde: str | None,
    fecha_hasta: str | None,
    log_prefijo: str,
) -> tuple[int, int]:
    """
    Borra ventas históricas (`ventas`). Si completo=True, también vacía `ventas_turno`.
    Devuelve (filas_ventas_borradas, filas_turno_borradas).
    """
    turno_del = 0
    qv = db.query(models.Venta).filter(models.Venta.sucursal_id == sucursal.id)

    if completo:
        turno_del = (
            db.query(models.VentaTurno)
            .filter(models.VentaTurno.sucursal_id == sucursal.id)
            .delete(synchronize_session=False)
        )
        ventas_del = qv.delete(synchronize_session=False)
    else:
        if fecha_desde and fecha_hasta:
            qv = qv.filter(models.Venta.fecha.between(fecha_desde.strip(), fecha_hasta.strip()))
        elif fecha_desde:
            qv = qv.filter(models.Venta.fecha >= fecha_desde.strip())
        elif fecha_hasta:
            qv = qv.filter(models.Venta.fecha <= fecha_hasta.strip())
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="En modo rango debes indicar al menos fecha_desde o fecha_hasta",
            )
        ventas_del = qv.delete(synchronize_session=False)

    sucursal.ultimo_checkpoint_historico = None
    msg = f"{log_prefijo} Borradas {ventas_del} venta(s) en histórico."
    if turno_del:
        msg += f" Eliminadas {turno_del} fila(s) de turno actual."
    msg += " Checkpoint del agente reseteado."
    db.add(
        models.LogSync(
            sucursal_id=sucursal.id,
            tipo="Limpieza",
            mensaje=msg,
        )
    )
    db.commit()
    return ventas_del, turno_del


def _dt_to_iso(v: datetime | None) -> str | None:
    if not v:
        return None
    # Si viene aware, normalizamos a UTC; si es naive, usamos isoformat directo.
    try:
        if getattr(v, "tzinfo", None) is not None:
            return v.astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    return v.isoformat()


@app.get("/admin/sucursales", response_model=List[schemas.SucursalBrief], tags=["Admin"])
def admin_list_sucursales(
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    rows = db.query(models.Sucursal).order_by(models.Sucursal.nombre).all()
    return [schemas.SucursalBrief(id=s.id, nombre=s.nombre) for s in rows]


@app.post("/admin/sucursales", response_model=schemas.SucursalBrief, tags=["Admin"])
def admin_create_sucursal(
    body: schemas.AdminCreateSucursalRequest,
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    nombre = body.nombre.strip().upper()

    existing = db.query(models.Sucursal).filter(models.Sucursal.nombre == nombre).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sucursal ya existe")

    suc = models.Sucursal(nombre=nombre)
    db.add(suc)
    try:
        db.commit()
        db.refresh(suc)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se pudo crear (conflicto)") from exc

    return schemas.SucursalBrief(id=suc.id, nombre=suc.nombre)


# ================================
# Swiss Tools Dashboard Admon (nuevo prefijo)
# ================================


@app.get("/swiss-admin/sucursales", response_model=List[schemas.SwissSucursalBrief], tags=["SwissAdmin"])
def swiss_admin_list_sucursales(
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    rows = db.query(models.Sucursal).order_by(models.Sucursal.nombre).all()
    return [
        schemas.SwissSucursalBrief(id=s.id, nombre=s.nombre, last_connection_at=_dt_to_iso(s.last_connection_at))
        for s in rows
    ]


@app.get(
    "/swiss-admin/sucursales/{sucursal_id}/logs",
    response_model=List[schemas.SwissSucursalLogsItem],
    tags=["SwissAdmin"],
)
def swiss_admin_sucursal_logs(
    sucursal_id: str,
    limit: int = 50,
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    logs = (
        db.query(models.LogSync)
        .filter(models.LogSync.sucursal_id == sucursal_id)
        .order_by(models.LogSync.fecha_registro.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    return [
        schemas.SwissSucursalLogsItem(
            id=log.id,
            tipo=log.tipo,
            mensaje=log.mensaje,
            fecha_registro=_dt_to_iso(log.fecha_registro),
            payload_invalido=log.payload_invalido,
        )
        for log in logs
    ]


@app.delete(
    "/swiss-admin/sucursales/{sucursal_id}/ventas-importadas",
    response_model=schemas.VentasImportadasPurgeResult,
    tags=["SwissAdmin"],
)
def swiss_admin_purge_ventas_importadas(
    sucursal_id: str,
    modo: schemas.VentasImportadasPurgeModo = Query(..., description="completo = todo histórico + turno; rango = solo ventas en fechas"),
    fecha_desde: str | None = Query(None, description="ISO fecha (YYYY-MM-DD), inclusive"),
    fecha_hasta: str | None = Query(None, description="ISO fecha (YYYY-MM-DD), inclusive"),
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Borra datos cargados por el agente de sync para una sucursal.
    `completo`: vacía `ventas` y `ventas_turno` y resetea checkpoint.
    `rango`: borra solo filas en `ventas` según fechas (al menos una fecha). No borra turno actual.
    """
    _require_admin(user)
    sucursal = db.query(models.Sucursal).filter(models.Sucursal.id == sucursal_id).first()
    if not sucursal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no registrada")

    if modo == schemas.VentasImportadasPurgeModo.completo:
        ventas_del, turno_del = _purge_ventas_importadas(
            db,
            sucursal,
            completo=True,
            fecha_desde=None,
            fecha_hasta=None,
            log_prefijo="[Portal Swiss]",
        )
        modo_str = "completo"
    else:
        fd = fecha_desde.strip() if fecha_desde and fecha_desde.strip() else None
        fh = fecha_hasta.strip() if fecha_hasta and fecha_hasta.strip() else None
        ventas_del, turno_del = _purge_ventas_importadas(
            db,
            sucursal,
            completo=False,
            fecha_desde=fd,
            fecha_hasta=fh,
            log_prefijo="[Portal Swiss] Rango fechas.",
        )
        modo_str = "rango"

    return schemas.VentasImportadasPurgeResult(
        status="Limpiado",
        registros_retirados=ventas_del,
        ventas_turno_eliminadas=turno_del,
        modo=modo_str,
        sucursal_nombre=sucursal.nombre,
    )


@app.post("/swiss-admin/sucursales", response_model=schemas.SwissSucursalBrief, tags=["SwissAdmin"])
def swiss_admin_create_sucursal(
    body: schemas.SwissAdminCreateSucursalRequest,
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    nombre = body.nombre.strip().upper()

    existing = db.query(models.Sucursal).filter(models.Sucursal.nombre == nombre).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sucursal ya existe")

    suc = models.Sucursal(
        nombre=nombre,
        sync_password_hash=hash_password(body.sync_password),
    )
    db.add(suc)
    try:
        db.commit()
        db.refresh(suc)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se pudo crear la sucursal") from exc

    return schemas.SwissSucursalBrief(id=suc.id, nombre=suc.nombre, last_connection_at=_dt_to_iso(suc.last_connection_at))


def _swiss_admin_purge_sucursal_relations(db: Session, suc: models.Sucursal) -> None:
    """
    Elimina en Supabase/Postgres toda la información ligada a la sucursal antes de borrar la fila:
    accesos de usuarios, catálogo compartido, turno actual, histórico de ventas, logs de sync
    (incluye checkpoint vía fila `sucursales`).
    """
    db.query(models.UsuarioSucursal).filter(models.UsuarioSucursal.sucursal_id == suc.id).delete(synchronize_session=False)
    db.query(models.CatalogoMaestroSucursal).filter(models.CatalogoMaestroSucursal.sucursal_id == suc.id).delete(
        synchronize_session=False
    )
    db.query(models.VentaTurno).filter(models.VentaTurno.sucursal_id == suc.id).delete(synchronize_session=False)
    db.query(models.Venta).filter(models.Venta.sucursal_id == suc.id).delete(synchronize_session=False)
    db.query(models.LogSync).filter(models.LogSync.sucursal_id == suc.id).delete(synchronize_session=False)


def _swiss_admin_delete_sucursal_core(db: Session, user: models.Usuario, sucursal_id: str) -> dict[str, str]:
    _require_admin(user)
    suc = db.query(models.Sucursal).filter(models.Sucursal.id == sucursal_id).first()
    if not suc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no registrada")
    _swiss_admin_purge_sucursal_relations(db, suc)
    db.delete(suc)
    db.commit()
    return {"status": "ok"}


@app.patch("/swiss-admin/sucursales/{sucursal_id}", response_model=schemas.SwissSucursalBrief, tags=["SwissAdmin"])
def swiss_admin_update_sucursal(
    sucursal_id: str,
    body: schemas.SwissAdminUpdateSucursalRequest,
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    suc = db.query(models.Sucursal).filter(models.Sucursal.id == sucursal_id).first()
    if not suc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no registrada")

    payload = body.model_dump(exclude_unset=True)
    if "sync_password" in payload and payload["sync_password"]:
        suc.sync_password_hash = hash_password(payload["sync_password"])
    db.commit()
    db.refresh(suc)
    return schemas.SwissSucursalBrief(id=suc.id, nombre=suc.nombre, last_connection_at=_dt_to_iso(suc.last_connection_at))


@app.delete("/swiss-admin/sucursales/{sucursal_id}", tags=["SwissAdmin"])
def swiss_admin_delete_sucursal(
    sucursal_id: str,
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _swiss_admin_delete_sucursal_core(db, user, sucursal_id)


@app.post("/swiss-admin/sucursales/{sucursal_id}/delete", tags=["SwissAdmin"])
def swiss_admin_delete_sucursal_post(
    sucursal_id: str,
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Misma semántica que DELETE /swiss-admin/sucursales/{id}; vía POST para entornos que
    devuelven 405 a DELETE (proxy, CDN, despliegues antiguos).
    """
    return _swiss_admin_delete_sucursal_core(db, user, sucursal_id)


@app.get("/admin/users", response_model=List[schemas.AdminUserBrief], tags=["Admin"])
def admin_list_users(
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    usuarios = db.query(models.Usuario).order_by(models.Usuario.email).all()

    out: List[schemas.AdminUserBrief] = []
    for u in usuarios:
        links = (
            db.query(models.UsuarioSucursal, models.Sucursal)
            .join(models.Sucursal, models.Sucursal.id == models.UsuarioSucursal.sucursal_id)
            .filter(models.UsuarioSucursal.usuario_id == u.id)
            .all()
        )
        sucursales = [
            schemas.SucursalBrief(id=s.id, nombre=s.nombre, rol=link.rol) for link, s in links
        ]
        out.append(
            schemas.AdminUserBrief(
                id=u.id,
                email=u.email,
                nombre=u.nombre,
                is_admin=u.is_admin,
                sucursales=sucursales,
            )
        )

    return out


@app.post("/admin/users", response_model=schemas.AdminUserBrief, tags=["Admin"])
def admin_create_user(
    body: schemas.AdminCreateUserRequest,
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)

    email = body.email.strip().lower()
    existing = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado")

    db_user = models.Usuario(
        email=email,
        password_hash=hash_password(body.password),
        nombre=(body.nombre.strip() if body.nombre else None),
        is_admin=body.is_admin,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Asignar sucursales si se proveen.
    created_links: List[models.UsuarioSucursal] = []
    if body.sucursal_ids:
        sucursales = db.query(models.Sucursal).filter(models.Sucursal.id.in_(body.sucursal_ids)).all()
        found_ids = {s.id for s in sucursales}
        missing = [sid for sid in body.sucursal_ids if sid not in found_ids]
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Sucursales no encontradas: {missing}")

        for s in sucursales:
            link = models.UsuarioSucursal(
                usuario_id=db_user.id,
                sucursal_id=s.id,
                rol=models.PermisoNivel.VISOR.value,
            )
            db.add(link)
            created_links.append(link)

        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se pudo asignar sucursales") from exc

    # Responder con sucursales actuales del usuario.
    links = (
        db.query(models.UsuarioSucursal, models.Sucursal)
        .join(models.Sucursal, models.Sucursal.id == models.UsuarioSucursal.sucursal_id)
        .filter(models.UsuarioSucursal.usuario_id == db_user.id)
        .all()
    )
    sucursales_out = [
        schemas.SucursalBrief(id=s.id, nombre=s.nombre, rol=link.rol) for link, s in links
    ]

    return schemas.AdminUserBrief(
        id=db_user.id,
        email=db_user.email,
        nombre=db_user.nombre,
        is_admin=db_user.is_admin,
        sucursales=sucursales_out,
    )


@app.get("/swiss-admin/users", response_model=List[schemas.SwissAdminUserBrief], tags=["SwissAdmin"])
def swiss_admin_list_dashboard_users(
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)

    usuarios = db.query(models.Usuario).filter(models.Usuario.portal_admin == False).order_by(models.Usuario.email).all()

    out: List[schemas.SwissAdminUserBrief] = []
    for u in usuarios:
        links = (
            db.query(models.UsuarioSucursal, models.Sucursal)
            .join(models.Sucursal, models.Sucursal.id == models.UsuarioSucursal.sucursal_id)
            .filter(models.UsuarioSucursal.usuario_id == u.id)
            .all()
        )
        sucursales = [schemas.SucursalBrief(id=s.id, nombre=s.nombre, rol=link.rol) for link, s in links]
        out.append(
            schemas.SwissAdminUserBrief(
                id=u.id,
                email=u.email,
                nombre=u.nombre,
                dashboard_access_until=_dt_to_iso(u.dashboard_access_until),
                last_dashboard_access_at=_dt_to_iso(u.last_dashboard_access_at),
                catalogo_maestro_id=u.catalogo_maestro_id,
                sucursales=sucursales,
            )
        )

    return out


@app.post("/swiss-admin/users", response_model=schemas.SwissAdminUserBrief, tags=["SwissAdmin"])
def swiss_admin_create_dashboard_user(
    body: schemas.SwissAdminCreateDashboardUserRequest,
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)

    email = body.email.strip().lower()
    existing = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado")

    portal_admin = False
    is_admin = False
    dashboard_access_until = None
    if body.dashboard_access_until:
        # Permitimos ISO string; lo guardamos tal cual en UTC.
        dashboard_access_until = datetime.fromisoformat(body.dashboard_access_until.replace("Z", "+00:00"))

    # Verificar catalogo opcional
    if body.catalogo_maestro_id:
        cat = db.query(models.CatalogoMaestro).filter(models.CatalogoMaestro.id == body.catalogo_maestro_id).first()
        if not cat:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="catalogo_maestro_id inválido")

    db_user = models.Usuario(
        email=email,
        password_hash=hash_password(body.password),
        nombre=(body.nombre.strip() if body.nombre else None),
        is_admin=is_admin,
        portal_admin=portal_admin,
        dashboard_access_until=dashboard_access_until,
        catalogo_maestro_id=body.catalogo_maestro_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    if body.sucursal_ids:
        sucursales = db.query(models.Sucursal).filter(models.Sucursal.id.in_(body.sucursal_ids)).all()
        found_ids = {s.id for s in sucursales}
        missing = [sid for sid in body.sucursal_ids if sid not in found_ids]
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Sucursales no encontradas: {missing}")

        for s in sucursales:
            db.add(
                models.UsuarioSucursal(
                    usuario_id=db_user.id,
                    sucursal_id=s.id,
                    rol=models.PermisoNivel.VISOR.value,
                )
            )
        db.commit()

    # Responder con sucursales y fechas actuales
    links = (
        db.query(models.UsuarioSucursal, models.Sucursal)
        .join(models.Sucursal, models.Sucursal.id == models.UsuarioSucursal.sucursal_id)
        .filter(models.UsuarioSucursal.usuario_id == db_user.id)
        .all()
    )
    sucursales_out = [schemas.SucursalBrief(id=s.id, nombre=s.nombre, rol=link.rol) for link, s in links]
    return schemas.SwissAdminUserBrief(
        id=db_user.id,
        email=db_user.email,
        nombre=db_user.nombre,
        dashboard_access_until=_dt_to_iso(db_user.dashboard_access_until),
        last_dashboard_access_at=_dt_to_iso(db_user.last_dashboard_access_at),
        catalogo_maestro_id=db_user.catalogo_maestro_id,
        sucursales=sucursales_out,
    )


@app.get("/swiss-admin/catalogos", response_model=List[schemas.SwissCatalogoBrief], tags=["SwissAdmin"])
def swiss_admin_list_catalogos(
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(requester)

    catalogs = db.query(models.CatalogoMaestro).order_by(models.CatalogoMaestro.nombre).all()
    out: List[schemas.SwissCatalogoBrief] = []

    for c in catalogs:
        suc_ids = [
            link.sucursal_id
            for link in db.query(models.CatalogoMaestroSucursal).filter(models.CatalogoMaestroSucursal.catalogo_id == c.id).all()
        ]
        prod_count = (
            db.query(models.CatalogoMaestroProducto)
            .filter(models.CatalogoMaestroProducto.catalogo_id == c.id)
            .count()
        )
        out.append(
            schemas.SwissCatalogoBrief(
                id=c.id,
                nombre=c.nombre,
                sucursal_ids=suc_ids,
                productos_count=prod_count,
            )
        )

    return out


@app.post("/swiss-admin/catalogos", response_model=schemas.SwissCatalogoBrief, tags=["SwissAdmin"])
def swiss_admin_create_catalogo(
    body: schemas.SwissCreateCatalogoRequest,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(requester)

    nombre = body.nombre.strip()
    existing = db.query(models.CatalogoMaestro).filter(models.CatalogoMaestro.nombre == nombre).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="catalogo ya existe")

    suc_ids = body.sucursal_ids or []
    sucursales = []
    found_ids = set()
    missing: List[str] = []
    if suc_ids:
        sucursales = db.query(models.Sucursal).filter(models.Sucursal.id.in_(suc_ids)).all()
        found_ids = {s.id for s in sucursales}
        missing = [sid for sid in suc_ids if sid not in found_ids]
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Sucursales no encontradas: {missing}")

    catalog = models.CatalogoMaestro(nombre=nombre)
    db.add(catalog)
    db.commit()
    db.refresh(catalog)

    # Asociaciones sucursales
    for s in sucursales:
        db.add(
            models.CatalogoMaestroSucursal(
                catalogo_id=catalog.id,
                sucursal_id=s.id,
            )
        )
    # Reglas fuzzy (alias_local -> nombre_maestro)
    for rule in body.reglas_productos or []:
        alias = (rule.alias_local or "").strip().upper()
        maestro = (rule.nombre_maestro or "").strip()
        if not alias or not maestro:
            continue
        db.add(
            models.CatalogoMaestroProducto(
                catalogo_id=catalog.id,
                nombre_maestro=maestro,
                alias_local=alias,
            )
        )

    db.commit()

    prod_count = (
        db.query(models.CatalogoMaestroProducto)
        .filter(models.CatalogoMaestroProducto.catalogo_id == catalog.id)
        .count()
    )
    return schemas.SwissCatalogoBrief(
        id=catalog.id,
        nombre=catalog.nombre,
        sucursal_ids=list(found_ids),
        productos_count=prod_count,
    )


@app.put("/swiss-admin/catalogos/{catalogo_id}", response_model=schemas.SwissCatalogoBrief, tags=["SwissAdmin"])
def swiss_admin_update_catalogo(
    catalogo_id: str,
    body: schemas.SwissUpdateCatalogoRequest,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(requester)

    catalog = db.query(models.CatalogoMaestro).filter(models.CatalogoMaestro.id == catalogo_id).first()
    if not catalog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="catalogo no encontrado")

    if body.nombre is not None:
        catalog.nombre = body.nombre.strip()

    if body.sucursal_ids is not None:
        # Reemplazo total de asociaciones
        db.query(models.CatalogoMaestroSucursal).filter(models.CatalogoMaestroSucursal.catalogo_id == catalogo_id).delete(
            synchronize_session=False
        )
        suc_ids = body.sucursal_ids or []
        if suc_ids:
            sucursales = db.query(models.Sucursal).filter(models.Sucursal.id.in_(suc_ids)).all()
            found_ids = {s.id for s in sucursales}
            missing = [sid for sid in suc_ids if sid not in found_ids]
            if missing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Sucursales no encontradas: {missing}")
            for s in sucursales:
                db.add(models.CatalogoMaestroSucursal(catalogo_id=catalogo_id, sucursal_id=s.id))

    if body.reglas_productos is not None:
        db.query(models.CatalogoMaestroProducto).filter(models.CatalogoMaestroProducto.catalogo_id == catalogo_id).delete(
            synchronize_session=False
        )
        for rule in body.reglas_productos or []:
            alias = (rule.alias_local or "").strip().upper()
            maestro = (rule.nombre_maestro or "").strip()
            if not alias or not maestro:
                continue
            db.add(
                models.CatalogoMaestroProducto(
                    catalogo_id=catalogo_id,
                    nombre_maestro=maestro,
                    alias_local=alias,
                )
            )

    db.commit()

    suc_ids = [
        link.sucursal_id
        for link in db.query(models.CatalogoMaestroSucursal).filter(models.CatalogoMaestroSucursal.catalogo_id == catalogo_id).all()
    ]
    prod_count = (
        db.query(models.CatalogoMaestroProducto)
        .filter(models.CatalogoMaestroProducto.catalogo_id == catalogo_id)
        .count()
    )

    return schemas.SwissCatalogoBrief(
        id=catalog.id,
        nombre=catalog.nombre,
        sucursal_ids=suc_ids,
        productos_count=prod_count,
    )


@app.get("/swiss-admin/config/admin-users", response_model=List[schemas.SwissAdminUserBrief], tags=["SwissAdmin"])
def swiss_admin_list_portal_admins(
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(requester)
    admins = db.query(models.Usuario).filter(models.Usuario.portal_admin == True).order_by(models.Usuario.email).all()

    out: List[schemas.SwissAdminUserBrief] = []
    for a in admins:
        out.append(
            schemas.SwissAdminUserBrief(
                id=a.id,
                email=a.email,
                nombre=a.nombre,
                dashboard_access_until=_dt_to_iso(a.dashboard_access_until),
                last_dashboard_access_at=_dt_to_iso(a.last_dashboard_access_at),
                catalogo_maestro_id=a.catalogo_maestro_id,
                sucursales=[],
            )
        )
    return out


@app.post("/swiss-admin/config/admin-users", response_model=schemas.SwissAdminUserBrief, tags=["SwissAdmin"])
def swiss_admin_create_portal_admin(
    body: schemas.SwissAdminCreatePortalAdminRequest,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(requester)
    email = body.email.strip().lower()
    existing = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado")

    db_user = models.Usuario(
        email=email,
        password_hash=hash_password(body.password),
        nombre=(body.nombre.strip() if body.nombre else None),
        is_admin=True,
        portal_admin=True,
        dashboard_access_until=None,
        catalogo_maestro_id=None,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return schemas.SwissAdminUserBrief(
        id=db_user.id,
        email=db_user.email,
        nombre=db_user.nombre,
        dashboard_access_until=_dt_to_iso(db_user.dashboard_access_until),
        last_dashboard_access_at=_dt_to_iso(db_user.last_dashboard_access_at),
        catalogo_maestro_id=db_user.catalogo_maestro_id,
        sucursales=[],
    )


@app.patch("/swiss-admin/config/admin-users/{user_id}/password", tags=["SwissAdmin"])
def swiss_admin_change_portal_admin_password(
    user_id: str,
    body: schemas.SwissChangePasswordRequest,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(requester)
    admin = db.query(models.Usuario).filter(models.Usuario.id == user_id, models.Usuario.portal_admin == True).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="admin no encontrado")

    if body.old_password:
        if not verify_password(body.old_password, admin.password_hash):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Contraseña actual incorrecta")

    admin.password_hash = hash_password(body.new_password)
    db.commit()
    return {"status": "ok"}


def _swiss_admin_delete_portal_admin_core(db: Session, requester: models.Usuario, user_id: str) -> dict[str, str]:
    _require_admin(requester)
    admin = db.query(models.Usuario).filter(models.Usuario.id == user_id, models.Usuario.portal_admin == True).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="admin no encontrado")
    db.delete(admin)
    db.commit()
    return {"status": "ok"}


@app.delete("/swiss-admin/config/admin-users/{user_id}", tags=["SwissAdmin"])
def swiss_admin_delete_portal_admin(
    user_id: str,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _swiss_admin_delete_portal_admin_core(db, requester, user_id)


@app.post("/swiss-admin/config/admin-users/{user_id}/delete", tags=["SwissAdmin"])
def swiss_admin_delete_portal_admin_post(
    user_id: str,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _swiss_admin_delete_portal_admin_core(db, requester, user_id)


@app.patch("/swiss-admin/config/admin-users/{user_id}", response_model=schemas.SwissAdminUserBrief, tags=["SwissAdmin"])
def swiss_admin_update_portal_admin(
    user_id: str,
    body: schemas.SwissUpdatePortalAdminRequest,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(requester)
    admin = db.query(models.Usuario).filter(models.Usuario.id == user_id, models.Usuario.portal_admin == True).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="admin no encontrado")

    if body.nombre is not None:
        admin.nombre = body.nombre.strip()
    if body.email is not None:
        new_email = body.email.strip().lower()
        if new_email != admin.email:
            exists = db.query(models.Usuario).filter(models.Usuario.email == new_email).first()
            if exists:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado")
            admin.email = new_email

    db.commit()
    db.refresh(admin)

    return schemas.SwissAdminUserBrief(
        id=admin.id,
        email=admin.email,
        nombre=admin.nombre,
        dashboard_access_until=_dt_to_iso(admin.dashboard_access_until),
        last_dashboard_access_at=_dt_to_iso(admin.last_dashboard_access_at),
        catalogo_maestro_id=admin.catalogo_maestro_id,
        sucursales=[],
    )


@app.patch("/swiss-admin/users/{user_id}/access", response_model=schemas.SwissAdminUserBrief, tags=["SwissAdmin"])
def swiss_admin_update_dashboard_user_access(
    user_id: str,
    body: schemas.SwissAdminUpdateDashboardUserAccessRequest,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(requester)

    db_user = db.query(models.Usuario).filter(models.Usuario.id == user_id, models.Usuario.portal_admin == False).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if body.dashboard_access_until is not None:
        if body.dashboard_access_until == "":
            db_user.dashboard_access_until = None
        else:
            db_user.dashboard_access_until = datetime.fromisoformat(body.dashboard_access_until.replace("Z", "+00:00"))

    db.commit()
    db.refresh(db_user)

    return _swiss_user_brief_from_db(db, db_user)


def _swiss_user_brief_from_db(db: Session, db_user: models.Usuario) -> schemas.SwissAdminUserBrief:
    links = (
        db.query(models.UsuarioSucursal, models.Sucursal)
        .join(models.Sucursal, models.Sucursal.id == models.UsuarioSucursal.sucursal_id)
        .filter(models.UsuarioSucursal.usuario_id == db_user.id)
        .all()
    )
    sucursales_out = [schemas.SucursalBrief(id=s.id, nombre=s.nombre, rol=link.rol) for link, s in links]
    return schemas.SwissAdminUserBrief(
        id=db_user.id,
        email=db_user.email,
        nombre=db_user.nombre,
        dashboard_access_until=_dt_to_iso(db_user.dashboard_access_until),
        last_dashboard_access_at=_dt_to_iso(db_user.last_dashboard_access_at),
        catalogo_maestro_id=db_user.catalogo_maestro_id,
        sucursales=sucursales_out,
    )


def _swiss_admin_delete_dashboard_user_core(
    db: Session, requester: models.Usuario, user_id: str
) -> dict[str, str]:
    _require_admin(requester)
    db_user = db.query(models.Usuario).filter(models.Usuario.id == user_id, models.Usuario.portal_admin == False).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.query(models.UsuarioSucursal).filter(models.UsuarioSucursal.usuario_id == db_user.id).delete(
        synchronize_session=False
    )
    db.delete(db_user)
    db.commit()
    return {"status": "ok"}


@app.patch("/swiss-admin/users/{user_id}", response_model=schemas.SwissAdminUserBrief, tags=["SwissAdmin"])
def swiss_admin_update_dashboard_user(
    user_id: str,
    body: schemas.SwissAdminUpdateDashboardUserRequest,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(requester)

    db_user = db.query(models.Usuario).filter(models.Usuario.id == user_id, models.Usuario.portal_admin == False).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    data = body.model_dump(exclude_unset=True)
    if not data:
        return _swiss_user_brief_from_db(db, db_user)

    if "password" in data and data["password"]:
        db_user.password_hash = hash_password(data["password"])

    if "nombre" in data:
        raw_n = data["nombre"]
        db_user.nombre = raw_n.strip() if isinstance(raw_n, str) and raw_n.strip() else None

    if "catalogo_maestro_id" in data:
        cid = data["catalogo_maestro_id"]
        if cid:
            cat = db.query(models.CatalogoMaestro).filter(models.CatalogoMaestro.id == cid).first()
            if not cat:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="catalogo_maestro_id inválido")
            db_user.catalogo_maestro_id = cid
        else:
            db_user.catalogo_maestro_id = None

    if "sucursal_ids" in data:
        ids = list(data["sucursal_ids"] or [])
        if not ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe quedar al menos una sucursal asignada",
            )
        sucursales = db.query(models.Sucursal).filter(models.Sucursal.id.in_(ids)).all()
        found_ids = {s.id for s in sucursales}
        missing = [sid for sid in ids if sid not in found_ids]
        if missing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Sucursales no encontradas: {missing}")

        db.query(models.UsuarioSucursal).filter(models.UsuarioSucursal.usuario_id == db_user.id).delete(
            synchronize_session=False
        )
        for s in sucursales:
            db.add(
                models.UsuarioSucursal(
                    usuario_id=db_user.id,
                    sucursal_id=s.id,
                    rol=models.PermisoNivel.VISOR.value,
                )
            )

    try:
        db.commit()
        db.refresh(db_user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se pudo actualizar el usuario") from exc

    return _swiss_user_brief_from_db(db, db_user)


@app.delete("/swiss-admin/users/{user_id}", tags=["SwissAdmin"])
def swiss_admin_delete_dashboard_user(
    user_id: str,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _swiss_admin_delete_dashboard_user_core(db, requester, user_id)


@app.post("/swiss-admin/users/{user_id}/delete", tags=["SwissAdmin"])
def swiss_admin_delete_dashboard_user_post(
    user_id: str,
    requester: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Misma semántica que DELETE /swiss-admin/users/{id}; POST evita 405 cuando DELETE está bloqueado.
    """
    return _swiss_admin_delete_dashboard_user_core(db, requester, user_id)


@app.get("/")
def home():
    return {"status": "ok", "message": "SwissTools Pos API en ejecución"}


@app.post("/auth/login", tags=["Auth"], response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.email == body.email.strip().lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    me = _user_me(db, user)
    token = create_access_token(
        sub=user.id,
        extra={"email": user.email, "is_admin": user.is_admin},
    )
    return schemas.TokenResponse(access_token=token, user=me)


@app.get("/auth/me", tags=["Auth"], response_model=schemas.UserMe)
def auth_me(
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _user_me(db, user)


@app.post("/auth/change-password", tags=["Auth"])
def change_password(
    body: schemas.ChangePasswordRequest,
    user: models.Usuario = Depends(get_current_user_dashboard),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Contraseña actual incorrecta")

    user.password_hash = hash_password(body.new_password)
    db.add(user)
    db.commit()
    return {"status": "ok"}


def _parse_date_iso(s: str):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def _prev_period_dates(fecha_desde: str, fecha_hasta: str) -> tuple[str, str]:
    d0 = _parse_date_iso(fecha_desde)
    d1 = _parse_date_iso(fecha_hasta)
    days = (d1 - d0).days + 1
    prev_end = d0 - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return prev_start.isoformat(), prev_end.isoformat()


def _pct_delta(cur: float, prev: float) -> Optional[float]:
    if prev == 0:
        return None if cur == 0 else None  # evitar infinito: sin referencia útil
    return round(((cur - prev) / prev) * 100, 2)


def _ventas_en_rango(
    db: Session,
    user: models.Usuario,
    fecha_desde: str,
    fecha_hasta: str,
    sucursal_id: Optional[str],
) -> List[models.Venta]:
    q = db.query(models.Venta).join(models.Sucursal, models.Venta.sucursal_id == models.Sucursal.id)

    if not user.is_admin:
        allowed_ids = [
            row.sucursal_id
            for row in db.query(models.UsuarioSucursal)
            .filter(models.UsuarioSucursal.usuario_id == user.id)
            .all()
        ]
        if not allowed_ids:
            return []
        q = q.filter(models.Venta.sucursal_id.in_(allowed_ids))

    if sucursal_id:
        q = q.filter(models.Venta.sucursal_id == sucursal_id)

    q = q.filter(models.Venta.fecha >= fecha_desde, models.Venta.fecha <= fecha_hasta)
    q = q.options(
        load_only(
            models.Venta.orden,
            models.Venta.fecha,
            models.Venta.hora,
            models.Venta.total_pagado,
            models.Venta.monto_efectivo,
            models.Venta.monto_tarjeta,
            models.Venta.metodo_pago_tarjeta,
            models.Venta.pagos,
            models.Venta.mesero_codigo,
            models.Venta.mesero_nombre,
            models.Venta.propinas,
            models.Venta.detalles,
        )
    )
    return q.all()


def _ventas_turno_en_rango(
    db: Session,
    user: models.Usuario,
    fecha_desde: str,
    fecha_hasta: str,
    sucursal_id: Optional[str],
) -> List[models.VentaTurno]:
    q = db.query(models.VentaTurno).join(models.Sucursal, models.VentaTurno.sucursal_id == models.Sucursal.id)

    if not user.is_admin:
        allowed_ids = [
            row.sucursal_id
            for row in db.query(models.UsuarioSucursal)
            .filter(models.UsuarioSucursal.usuario_id == user.id)
            .all()
        ]
        if not allowed_ids:
            return []
        q = q.filter(models.VentaTurno.sucursal_id.in_(allowed_ids))

    if sucursal_id:
        q = q.filter(models.VentaTurno.sucursal_id == sucursal_id)

    q = q.filter(models.VentaTurno.fecha >= fecha_desde, models.VentaTurno.fecha <= fecha_hasta)
    q = q.options(
        load_only(
            models.VentaTurno.orden,
            models.VentaTurno.fecha,
            models.VentaTurno.hora,
            models.VentaTurno.total_pagado,
            models.VentaTurno.monto_efectivo,
            models.VentaTurno.monto_tarjeta,
            models.VentaTurno.metodo_pago_tarjeta,
            models.VentaTurno.pagos,
            models.VentaTurno.mesero_codigo,
            models.VentaTurno.mesero_nombre,
            models.VentaTurno.propinas,
            models.VentaTurno.detalles,
        )
    )
    return q.all()


def _ventas_merged_para_resumen(
    db: Session,
    user: models.Usuario,
    fecha_desde: str,
    fecha_hasta: str,
    sucursal_id: Optional[str],
) -> List[Any]:
    """Histórico + turno en curso, sin duplicar ORDEN ya cerrado en histórico."""
    hist = _ventas_en_rango(db, user, fecha_desde, fecha_hasta, sucursal_id)
    ordenes_hist: set[str] = set()
    for v in hist:
        o = (v.orden or "").strip()
        if o:
            ordenes_hist.add(o)
    turno = _ventas_turno_en_rango(db, user, fecha_desde, fecha_hasta, sucursal_id)
    turno_filtrado = [t for t in turno if (t.orden or "").strip() not in ordenes_hist]
    return list(hist) + list(turno_filtrado)


def _montos_efectivo_tarjeta_row(v: Any) -> tuple[float, float]:
    pagos = getattr(v, "pagos", None) or []
    if pagos and isinstance(pagos, list):
        ef = 0.0
        tar = 0.0
        for p in pagos:
            if not isinstance(p, dict):
                continue
            amt = float(p.get("amount") or 0)
            if amt <= 0:
                continue
            kind = (p.get("kind") or "").strip().lower()
            if kind == "efectivo":
                ef += amt
            elif kind == "tarjeta":
                tar += amt
            elif kind == "otro":
                continue
            elif (p.get("name") or "").strip().lower() == "efectivo":
                ef += amt
            else:
                continue
        if ef > 0 or tar > 0 or pagos:
            return ef, tar
    return float(v.monto_efectivo or 0), float(v.monto_tarjeta or 0)


def _acumular_pagos_en_map(v: Any, metodo_map: dict[str, float]) -> None:
    pagos = getattr(v, "pagos", None) or []
    if pagos and isinstance(pagos, list):
        for p in pagos:
            if not isinstance(p, dict):
                continue
            amt = float(p.get("amount") or 0)
            if amt <= 0:
                continue
            name = (str(p.get("name") or "Otro")).strip() or "Otro"
            metodo_map[name] += amt
        return
    label = (getattr(v, "metodo_pago_tarjeta", None) or "N/A").strip() or "N/A"
    metodo_map[label] += float(v.monto_tarjeta or 0)
    metodo_map["Efectivo"] += float(v.monto_efectivo or 0)


def _detalle_line_costo(item: dict) -> float:
    for k in ("costo_renglon", "cosven"):
        v = item.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return 0.0


def _bucket_hora_par(hour: int) -> str:
    h = max(0, min(23, int(hour)))
    b = (h // 2) * 2
    return f"{b:02d}:00"


_WD_LABELS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")


def _estimar_comisiones_tarjetas(metodo_map: dict[str, float]) -> dict[str, Any]:
    detalle: list[dict[str, Any]] = []
    for name, amt in metodo_map.items():
        amt_f = float(amt)
        if amt_f <= 0:
            continue
        n = str(name).upper().strip()
        rate = 0.0
        if n == "EFECTIVO" or (n.startswith("EFECT") and "TAR" not in n):
            rate = 0.0
        elif "AMEX" in n or "AMERICAN" in n:
            rate = 0.042
        elif "DEBITO" in n or "DÉBITO" in n or n.startswith("TD"):
            rate = 0.015
        elif (
            "CREDITO" in n
            or "CRÉDITO" in n
            or n.startswith("TC")
            or "VISA" in n
            or "MASTERCARD" in n
            or "MASTER" in n
        ):
            rate = 0.0225
        if rate <= 0:
            continue
        com = round(amt_f * rate, 2)
        detalle.append(
            {
                "metodo": name,
                "monto": round(amt_f, 2),
                "tasa_pct": round(rate * 100, 2),
                "comision": com,
            }
        )
    base = round(sum(d["monto"] for d in detalle), 2)
    total_com = round(sum(d["comision"] for d in detalle), 2)
    return {
        "total_comision": total_com,
        "base_tarjeta": base,
        "detalle": detalle,
    }


def _resumen_from_ventas(ventas: List[Any]) -> dict[str, Any]:
    empty = {
        "total_ingresos": 0.0,
        "num_tickets": 0,
        "ticket_promedio": 0.0,
        "total_efectivo": 0.0,
        "total_tarjeta": 0.0,
        "total_costo": 0.0,
        "utilidad_bruta": 0.0,
        "margen_pct": None,
        "total_propinas": 0.0,
        "total_anulaciones_monto": 0.0,
        "por_hora": [],
        "por_hora_semana": [],
        "por_metodo": [],
        "por_dia": [],
        "top_productos": [],
        "por_mesero": [],
        "por_clase": [],
        "resumen_financiero": None,
        "comisiones_estimadas": None,
    }
    if not ventas:
        return empty

    total_ingresos = sum(float(v.total_pagado or 0) for v in ventas)
    num = len(ventas)
    total_efectivo = sum(_montos_efectivo_tarjeta_row(v)[0] for v in ventas)
    total_tarjeta = sum(_montos_efectivo_tarjeta_row(v)[1] for v in ventas)
    total_propinas = sum(float(getattr(v, "propinas", None) or 0) for v in ventas)

    total_costo = 0.0
    for v in ventas:
        for item in v.detalles or []:
            if isinstance(item, dict):
                total_costo += _detalle_line_costo(item)

    utilidad_bruta = total_ingresos - total_costo
    margen_pct: Optional[float] = None
    if total_ingresos > 0 and total_costo > 0:
        margen_pct = round((1.0 - total_costo / total_ingresos) * 100, 1)

    ingreso_neto_iva = total_ingresos / 1.16 if total_ingresos else 0.0
    iva_estimado = total_ingresos - ingreso_neto_iva if total_ingresos else 0.0

    por_hora: dict[str, float] = defaultdict(float)
    slot_week: dict[str, list[float]] = defaultdict(lambda: [0.0] * 7)

    for v in ventas:
        h = (v.hora or "").strip()[:5] or "00:00"
        por_hora[h] += float(v.total_pagado or 0)

        fstr = (v.fecha or "").strip()[:10]
        if fstr:
            try:
                wd = date.fromisoformat(fstr).weekday()
            except ValueError:
                wd = None
            if wd is not None:
                hparts = (v.hora or "00:00").replace(".", ":").split(":")
                try:
                    hh = int(hparts[0]) if hparts and str(hparts[0]).strip() != "" else 0
                except ValueError:
                    hh = 0
                slot = _bucket_hora_par(hh)
                slot_week[slot][wd] += float(v.total_pagado or 0)

    metodo_map: dict[str, float] = defaultdict(float)
    for v in ventas:
        _acumular_pagos_en_map(v, metodo_map)

    comisiones_info = _estimar_comisiones_tarjetas(dict(metodo_map))
    resumen_financiero = {
        "ingreso_bruto": round(total_ingresos, 2),
        "iva_estimado": round(iva_estimado, 2),
        "ingreso_neto": round(ingreso_neto_iva, 2),
        "costo_ventas": round(total_costo, 2),
        "utilidad_bruta": round(utilidad_bruta, 2),
        "comisiones_tarjeta": comisiones_info["total_comision"],
        "propinas_total": round(total_propinas, 2),
    }

    hora_sorted = sorted(por_hora.keys())
    por_hora_list = [{"name": f"{h}", "ventas": round(por_hora[h], 2)} for h in hora_sorted]
    por_metodo = [{"name": k, "amount": round(metodo_map[k], 2)} for k in sorted(metodo_map, key=lambda x: -metodo_map[x])]

    por_dia_acc: dict[str, dict[str, Any]] = {}
    for v in ventas:
        f = (v.fecha or "").strip() or ""
        ef, tar = _montos_efectivo_tarjeta_row(v)
        if f not in por_dia_acc:
            por_dia_acc[f] = {
                "fecha": f,
                "total_pagado": 0.0,
                "num_tickets": 0,
                "total_efectivo": 0.0,
                "total_tarjeta": 0.0,
                "total_costo": 0.0,
            }
        por_dia_acc[f]["total_pagado"] += float(v.total_pagado or 0)
        por_dia_acc[f]["num_tickets"] += 1
        por_dia_acc[f]["total_efectivo"] += ef
        por_dia_acc[f]["total_tarjeta"] += tar
        for item in v.detalles or []:
            if isinstance(item, dict):
                por_dia_acc[f]["total_costo"] += _detalle_line_costo(item)

    por_dia_sorted = sorted(por_dia_acc.keys())
    por_dia_list = [
        {
            "fecha": por_dia_acc[f]["fecha"],
            "total_pagado": round(por_dia_acc[f]["total_pagado"], 2),
            "num_tickets": por_dia_acc[f]["num_tickets"],
            "total_efectivo": round(por_dia_acc[f]["total_efectivo"], 2),
            "total_tarjeta": round(por_dia_acc[f]["total_tarjeta"], 2),
            "total_costo": round(por_dia_acc[f]["total_costo"], 2),
        }
        for f in por_dia_sorted
    ]

    def _slot_sort_key(s: str) -> int:
        try:
            return int(s.split(":")[0])
        except (ValueError, IndexError):
            return 0

    por_hora_semana: list[dict[str, Any]] = []
    for slot in sorted(slot_week.keys(), key=_slot_sort_key):
        vals = slot_week[slot]
        if sum(vals) <= 0:
            continue
        row: dict[str, Any] = {"hora": slot}
        for i, lab in enumerate(_WD_LABELS):
            if vals[i] > 0:
                row[lab] = round(vals[i], 2)
        por_hora_semana.append(row)

    prod_acc: dict[str, dict[str, Any]] = {}
    clase_acc: dict[int, dict[str, Any]] = {}
    clase_nombres = {1: "Artículos (CLASE 1)", 2: "Alimentos (CLASE 2)"}

    for v in ventas:
        for item in v.detalles or []:
            if not isinstance(item, dict):
                continue
            desc = (str(item.get("descripcion") or "")).strip()
            cod = (str(item.get("codigo") or "")).strip()
            nombre = desc or cod or "Sin descripción"
            key = desc or cod or nombre
            tr = float(item.get("total_renglon") or 0)
            cant = float(item.get("cantidad") or 0)
            c_line = _detalle_line_costo(item)
            if key not in prod_acc:
                prod_acc[key] = {
                    "nombre": nombre,
                    "codigo": cod or None,
                    "total_renglon": 0.0,
                    "total_costo": 0.0,
                    "cantidad": 0.0,
                }
            prod_acc[key]["total_renglon"] += tr
            prod_acc[key]["total_costo"] += c_line
            prod_acc[key]["cantidad"] += cant

            clase_raw = item.get("clase")
            try:
                clase_i = int(clase_raw) if clase_raw is not None and str(clase_raw).strip() != "" else 0
            except (TypeError, ValueError):
                clase_i = 0
            if clase_i in (1, 2):
                if clase_i not in clase_acc:
                    clase_acc[clase_i] = {"name": clase_nombres[clase_i], "total_renglon": 0.0, "cantidad": 0.0}
                clase_acc[clase_i]["total_renglon"] += tr
                clase_acc[clase_i]["cantidad"] += cant

    top_sorted = sorted(prod_acc.values(), key=lambda x: -x["total_renglon"])[:20]
    top_productos = []
    for p in top_sorted:
        trn = p["total_renglon"]
        tc = p["total_costo"]
        m_pct = None
        if trn > 0 and tc > 0:
            m_pct = round((1.0 - tc / trn) * 100, 1)
        top_productos.append(
            {
                "nombre": p["nombre"],
                "codigo": p["codigo"],
                "total_renglon": round(trn, 2),
                "total_costo": round(tc, 2),
                "margen_pct": m_pct,
                "cantidad": round(p["cantidad"], 3),
            }
        )

    mesero_acc: dict[str, dict[str, Any]] = {}
    for v in ventas:
        cod = (getattr(v, "mesero_codigo", None) or "").strip()
        if not cod:
            continue
        nom = (getattr(v, "mesero_nombre", None) or "").strip() or cod
        tip = float(getattr(v, "propinas", None) or 0)
        if cod not in mesero_acc:
            mesero_acc[cod] = {"codigo": cod, "nombre": nom, "total_pagado": 0.0, "num_tickets": 0, "propinas": 0.0}
        mesero_acc[cod]["total_pagado"] += float(v.total_pagado or 0)
        mesero_acc[cod]["num_tickets"] += 1
        mesero_acc[cod]["propinas"] += tip

    por_mesero = sorted(mesero_acc.values(), key=lambda x: -x["total_pagado"])[:30]
    por_mesero_out: list[dict[str, Any]] = []
    for m in por_mesero:
        tp = m["total_pagado"]
        nt = m["num_tickets"]
        por_mesero_out.append(
            {
                "codigo": m["codigo"],
                "nombre": m["nombre"],
                "total_pagado": round(tp, 2),
                "num_tickets": nt,
                "propinas": round(m["propinas"], 2),
                "ticket_promedio": round(tp / nt, 2) if nt else 0.0,
            }
        )

    por_clase = sorted(
        [
            {
                "name": clase_acc[k]["name"],
                "total_renglon": round(clase_acc[k]["total_renglon"], 2),
                "cantidad": round(clase_acc[k]["cantidad"], 3),
            }
            for k in sorted(clase_acc.keys())
        ],
        key=lambda x: -x["total_renglon"],
    )

    return {
        "total_ingresos": round(total_ingresos, 2),
        "num_tickets": num,
        "ticket_promedio": round(total_ingresos / num, 2) if num else 0.0,
        "total_efectivo": round(total_efectivo, 2),
        "total_tarjeta": round(total_tarjeta, 2),
        "total_costo": round(total_costo, 2),
        "utilidad_bruta": round(utilidad_bruta, 2),
        "margen_pct": margen_pct,
        "total_propinas": round(total_propinas, 2),
        "total_anulaciones_monto": 0.0,
        "por_hora": por_hora_list,
        "por_hora_semana": por_hora_semana,
        "por_metodo": por_metodo[:12],
        "por_dia": por_dia_list,
        "top_productos": top_productos,
        "por_mesero": por_mesero_out,
        "por_clase": por_clase,
        "resumen_financiero": resumen_financiero,
        "comisiones_estimadas": comisiones_info,
    }


@app.get("/dashboard/resumen", tags=["Dashboard"])
def dashboard_resumen(
    fecha_desde: str,
    fecha_hasta: str,
    sucursal_id: Optional[str] = None,
    include_previous: bool = False,
    user: models.Usuario = Depends(get_current_user_dashboard),
    db: Session = Depends(get_db),
):
    """
    KPIs y series para el dashboard. Admin ve todas las sucursales; visor solo las asignadas en usuario_sucursales.
    Incluye por_dia, top_productos (desde detalles JSON) y deltas opcionales vs el periodo anterior de igual duración.
    """
    ventas = _ventas_merged_para_resumen(db, user, fecha_desde, fecha_hasta, sucursal_id)
    out = _resumen_from_ventas(ventas)

    if include_previous:
        pd, ph = _prev_period_dates(fecha_desde, fecha_hasta)
        prev_ventas = _ventas_merged_para_resumen(db, user, pd, ph, sucursal_id)
        prev = _resumen_from_ventas(prev_ventas)
        out["deltas"] = {
            "total_ingresos_pct": _pct_delta(out["total_ingresos"], prev["total_ingresos"]),
            "num_tickets_pct": _pct_delta(float(out["num_tickets"]), float(prev["num_tickets"])),
            "ticket_promedio_pct": _pct_delta(out["ticket_promedio"], prev["ticket_promedio"]),
            "total_costo_pct": _pct_delta(out.get("total_costo", 0.0), prev.get("total_costo", 0.0)),
            "utilidad_bruta_pct": _pct_delta(out.get("utilidad_bruta", 0.0), prev.get("utilidad_bruta", 0.0)),
            "total_propinas_pct": _pct_delta(out.get("total_propinas", 0.0), prev.get("total_propinas", 0.0)),
        }

    return out


@app.get("/dashboard/sucursales", tags=["Dashboard"])
def list_sucursales_for_filter(
    user: models.Usuario = Depends(get_current_user_dashboard),
    db: Session = Depends(get_db),
):
    if user.is_admin:
        rows = db.query(models.Sucursal).order_by(models.Sucursal.nombre).all()
    else:
        rows = (
            db.query(models.Sucursal)
            .join(models.UsuarioSucursal, models.UsuarioSucursal.sucursal_id == models.Sucursal.id)
            .filter(models.UsuarioSucursal.usuario_id == user.id)
            .order_by(models.Sucursal.nombre)
            .all()
        )
    return [{"id": s.id, "nombre": s.nombre} for s in rows]


# ================================
# ENDPOINTS CONTROL Y PAUSA (Tarea 2.2)
# ================================
@app.post("/sync/pause/{sucursal_nombre}", tags=["Control"])
def pause_sync(sucursal_nombre: str, db: Session = Depends(get_db)):
    sucursal = db.query(models.Sucursal).filter(models.Sucursal.nombre == sucursal_nombre).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no registrada")

    sucursal.sync_paused = True
    db.commit()
    return {"status": "Pausado", "sucursal": sucursal_nombre, "mensaje": "Se rechazará flujo del agente temporalmente."}


@app.post("/sync/resume/{sucursal_nombre}", tags=["Control"])
def resume_sync(sucursal_nombre: str, db: Session = Depends(get_db)):
    sucursal = db.query(models.Sucursal).filter(models.Sucursal.nombre == sucursal_nombre).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no registrada")

    sucursal.sync_paused = False
    db.commit()
    return {"status": "Reanudado", "sucursal": sucursal_nombre, "mensaje": "Recepción reactivada."}


# ================================
# ENDPOINT DE GESTIÓN MANTENIMIENTO (Tarea 2.3)
# ================================
@app.delete("/admin/limpieza/{sucursal_nombre}", tags=["Mantenimiento"])
def limpieza_reset(
    sucursal_nombre: str,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """API legada: con `fecha_inicio` y `fecha_fin` borra solo ese rango en histórico; sin ambos, borra todo + turno."""
    _require_maintenance_access(user)
    sucursal = db.query(models.Sucursal).filter(models.Sucursal.nombre == sucursal_nombre.strip()).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no registrada")

    if fecha_inicio and fecha_fin:
        borrados, turno_del = _purge_ventas_importadas(
            db,
            sucursal,
            completo=False,
            fecha_desde=fecha_inicio.strip(),
            fecha_hasta=fecha_fin.strip(),
            log_prefijo="[API /admin/limpieza]",
        )
    else:
        borrados, turno_del = _purge_ventas_importadas(
            db,
            sucursal,
            completo=True,
            fecha_desde=None,
            fecha_hasta=None,
            log_prefijo="[API /admin/limpieza]",
        )

    return {
        "status": "Limpiado",
        "registros_retirados": borrados,
        "ventas_turno_eliminadas": turno_del,
    }


# ================================
# ENDPOINT FASE 4: CATÁLOGO E INTELIGENCIA (Tarea 4.1, 4.2, 4.3)
# ================================
@app.get("/admin/export/top10", tags=["Reportes"])
def exportar_top_10_csv(
    user: models.Usuario = Depends(get_current_user_dashboard),
    db: Session = Depends(get_db),
):
    sucursal_ids = None
    if not user.is_admin:
        sucursal_ids = [
            row.sucursal_id
            for row in db.query(models.UsuarioSucursal)
            .filter(models.UsuarioSucursal.usuario_id == user.id)
            .all()
        ]

    etl = ETLMatcher(
        db,
        catalogo_maestro_id=user.catalogo_maestro_id,
        sucursal_ids=sucursal_ids,
    )
    csv_content = etl.export_top10_to_csv()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=top10_platillos_consolidado.csv"},
    )


# ================================
# ENDPOINT INGESTA SYNC AGENT (Tarea 2.4/2.1)
# ================================
def _sync_float_field(v: Any, default: float = 0.0) -> float:
    try:
        n = float(v if v is not None else default)
        return n if n == n and n not in (float("inf"), float("-inf")) else default
    except (TypeError, ValueError):
        return default


def _sync_optional_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        n = float(v)
        return n if n == n and n not in (float("inf"), float("-inf")) else None
    except (TypeError, ValueError):
        return None


def _sync_normalize_fecha(raw: Any) -> str:
    """Parte YYYY-MM-DD aunque el agente envíe ISO con hora (p. ej. desde datetime en DBF)."""
    s = str(raw or "").strip()
    if len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-":
        return s[:10]
    return s


def _sync_normalize_hora(raw: Any) -> str:
    """HH:MM estable desde '19:48', '19:48:00', '9:5', etc."""
    s = str(raw or "").strip().replace(".", ":")
    if not s:
        return "00:00"
    parts = [p for p in s.split(":") if p != ""]
    if not parts:
        return "00:00"
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return "00:00"
    h = max(0, min(23, h))
    m = max(0, min(59, m))
    return f"{h:02d}:{m:02d}"


def _sync_venta_pk_parts(sucursal_nombre: str, v: dict, orden: str) -> tuple[str, str, str]:
    fecha = _sync_normalize_fecha(v.get("fecha"))
    hora = _sync_normalize_hora(v.get("hora"))
    pk = f"{sucursal_nombre}_{fecha}_{hora}_{orden}"
    return pk, fecha, hora


def _dedupe_historial_por_pk(sucursal_nombre: str, historial: list) -> tuple[list, int]:
    """Último gana por id compuesto; preserva entradas sin orden para los logs de error."""
    seen: dict[str, dict] = {}
    sin_orden: list[dict] = []
    dupes = 0
    for v in historial:
        orden = str(v.get("orden", "")).strip()
        if not orden:
            sin_orden.append(v)
            continue
        pk, _, _ = _sync_venta_pk_parts(sucursal_nombre, v, orden)
        if pk in seen:
            dupes += 1
        seen[pk] = v
    return list(seen.values()) + sin_orden, dupes


def _venta_row_dict(
    pk: str,
    sucursal_id: str,
    orden: str,
    kw: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": pk,
        "sucursal_id": sucursal_id,
        "orden": orden,
        "factura": kw.get("factura"),
        "fecha": kw.get("fecha"),
        "hora": kw.get("hora"),
        "total_pagado": kw.get("total_pagado", 0),
        "subtotal": kw.get("subtotal", 0),
        "metodo_pago_tarjeta": kw.get("metodo_pago_tarjeta", "N/A"),
        "monto_tarjeta": kw.get("monto_tarjeta", 0),
        "monto_efectivo": kw.get("monto_efectivo", 0),
        "pagos": kw.get("pagos"),
        "mesero_codigo": kw.get("mesero_codigo"),
        "mesero_nombre": kw.get("mesero_nombre"),
        "propinas": kw.get("propinas"),
        "detalles": kw.get("detalles", []),
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
    }


def _insert_venta_idempotent(db: Session, row: dict[str, Any]) -> bool:
    """
    Inserta venta si no existe la PK. PostgreSQL/SQLite: ON CONFLICT DO NOTHING + RETURNING.
    Evita 500 por reenvío de lote, réplicas de lectura o carreras entre workers.
    """
    tbl = models.Venta.__table__
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        stmt = (
            pg_insert(tbl)
            .values(**row)
            .on_conflict_do_nothing(index_elements=[tbl.c.id])
            .returning(tbl.c.id)
        )
        res = db.execute(stmt)
        return res.fetchone() is not None
    if dialect == "sqlite":
        stmt = (
            sqlite_insert(tbl)
            .values(**row)
            .on_conflict_do_nothing(index_elements=[tbl.c.id])
            .returning(tbl.c.id)
        )
        res = db.execute(stmt)
        return res.fetchone() is not None
    if db.get(models.Venta, row["id"]):
        return False
    db.add(models.Venta(**row))
    return True


def _insert_venta_turno_idempotent(db: Session, row: dict[str, Any]) -> bool:
    """Inserta en ventas_turno sin romper por PK duplicada."""
    tbl = models.VentaTurno.__table__
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        stmt = (
            pg_insert(tbl)
            .values(**row)
            .on_conflict_do_nothing(index_elements=[tbl.c.id])
            .returning(tbl.c.id)
        )
        res = db.execute(stmt)
        return res.fetchone() is not None
    if dialect == "sqlite":
        stmt = (
            sqlite_insert(tbl)
            .values(**row)
            .on_conflict_do_nothing(index_elements=[tbl.c.id])
            .returning(tbl.c.id)
        )
        res = db.execute(stmt)
        return res.fetchone() is not None
    if db.get(models.VentaTurno, row["id"]):
        return False
    db.add(models.VentaTurno(**row))
    return True


def _dedupe_turno_por_orden(turno_rows: list) -> tuple[list, int]:
    """
    El snapshot FACTURA1T/2T puede traer ORDEN repetido.
    Conservamos el último por ORDEN para evitar choques de PK en ventas_turno.
    """
    seen: dict[str, dict] = {}
    sin_orden: list[dict] = []
    dupes = 0
    for v in turno_rows:
        orden = str(v.get("orden", "")).strip()
        if not orden:
            sin_orden.append(v)
            continue
        if orden in seen:
            dupes += 1
        seen[orden] = v
    return list(seen.values()) + sin_orden, dupes


def _sync_payload_to_venta_kwargs(v: dict) -> dict[str, Any]:
    return {
        "factura": v.get("factura"),
        "fecha": v.get("fecha"),
        "hora": v.get("hora"),
        "total_pagado": _sync_float_field(v.get("total_pagado"), 0),
        "subtotal": _sync_float_field(v.get("subtotal"), 0),
        "metodo_pago_tarjeta": v.get("metodo_pago_tarjeta", "N/A"),
        "monto_tarjeta": _sync_float_field(v.get("monto_tarjeta"), 0),
        "monto_efectivo": _sync_float_field(v.get("monto_efectivo"), 0),
        "pagos": v.get("pagos"),
        "mesero_codigo": v.get("mesero_codigo"),
        "mesero_nombre": v.get("mesero_nombre"),
        "propinas": _sync_optional_float(v.get("propinas")),
        "detalles": v.get("detalles", []) if isinstance(v.get("detalles"), list) else [],
    }


def _sync_resolve_sucursal_y_auth(
    db: Session,
    sucursal_nombre: str,
    sucursal_password: str | None,
    *,
    actualizar_last_connection: bool,
) -> models.Sucursal:
    """Valida sucursal + X-Sucursal-Password para el agente (sync)."""
    sucursal_nombre_u = sucursal_nombre.strip().upper()
    sucursal = db.query(models.Sucursal).filter(models.Sucursal.nombre == sucursal_nombre_u).first()

    if not sucursal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no registrada")

    if not sucursal.sync_password_hash:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sucursal sin credencial de sync configurada")

    if not sucursal_password or not verify_password(sucursal_password, sucursal.sync_password_hash):
        db.add(
            models.LogSync(
                sucursal_id=sucursal.id,
                tipo="Auth",
                mensaje="Credenciales sync inválidas (X-Sucursal-Password).",
                payload_invalido=None,
            )
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales sync inválidas")

    if actualizar_last_connection:
        try:
            sucursal.last_connection_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()

    if sucursal.sync_paused:
        raise HTTPException(status_code=503, detail="Sync pausado para esta sucursal.")

    return sucursal


@app.get("/sync/last-orden/{sucursal_nombre}", tags=["Sincronización"])
def sync_last_orden(
    sucursal_nombre: str,
    db: Session = Depends(get_db),
    sucursal_password: str | None = Header(None, alias="X-Sucursal-Password"),
):
    """
    Mayor `orden` numérico ya persistido para la sucursal (FACTURA1.ORDEN).
    El agente lo usa para alinear el checkpoint local con la nube tras errores o otra PC.
    """
    sucursal = _sync_resolve_sucursal_y_auth(db, sucursal_nombre, sucursal_password, actualizar_last_connection=False)
    try:
        mx = (
            db.query(func.max(cast(models.Venta.orden, BigInteger)))
            .filter(models.Venta.sucursal_id == sucursal.id)
            .scalar()
        )
    except Exception:
        db.rollback()
        dialect = db.get_bind().dialect.name
        mx = None
        if dialect == "postgresql":
            try:
                mx = db.execute(
                    text(
                        """
                        SELECT MAX(CAST(orden AS BIGINT))
                        FROM ventas
                        WHERE sucursal_id = :sid AND orden ~ '^[0-9]+$'
                        """
                    ),
                    {"sid": sucursal.id},
                ).scalar()
            except Exception:
                db.rollback()
                mx = None
        if mx is None:
            stmt = select(models.Venta.orden).where(models.Venta.sucursal_id == sucursal.id)
            res = db.execute(stmt)
            for o in res.scalars().yield_per(4000):
                try:
                    n = int(str(o).strip())
                except ValueError:
                    continue
                mx = n if mx is None else max(mx, n)
    if mx is None:
        return {"last_orden": None, "sucursal": sucursal.nombre}
    return {"last_orden": str(int(mx)), "sucursal": sucursal.nombre}


@app.post("/sync/upload/{sucursal_nombre}", tags=["Sincronización"])
def upload_sync_data(
    sucursal_nombre: str,
    payload: dict,
    db: Session = Depends(get_db),
    sucursal_password: str | None = Header(None, alias="X-Sucursal-Password"),
):
    """
    Recepción del agente en cada PC.
    Autenticación por sucursal: `X-Sucursal-Password`.
    Body: `historial` (incremental FACTURA1/2), opcional `turno_actual` (snapshot FACTURA1T/2T por ciclo).
    """
    sucursal = _sync_resolve_sucursal_y_auth(
        db, sucursal_nombre, sucursal_password, actualizar_last_connection=True
    )

    historial = payload.get("historial") or []
    nuevas_inserciones = 0
    errores_detectados = 0
    turno_filas = 0
    mesero_historial_backfill = 0

    try:
        # Asegura columnas nuevas (p. ej. propinas) si el arranque falló o la DB no tenía migración aplicada.
        try:
            ensure_schema_columns()
        except Exception:
            logger.exception("ensure_schema_columns falló durante /sync/upload; se continúa con esquema actual")
        historial_proc, historial_dupes = _dedupe_historial_por_pk(sucursal.nombre, historial)
        if historial_dupes:
            logger.info(
                "sync %s: historial con %s filas duplicadas por PK (misma sucursal/fecha/hora/orden); se procesa la última",
                sucursal.nombre,
                historial_dupes,
            )
        for v in historial_proc:
            orden = str(v.get("orden", "")).strip()
            if not orden:
                db.add(
                    models.LogSync(
                        sucursal_id=sucursal.id,
                        tipo="Error Crítico ORDEN",
                        mensaje="Dato huérfano detectado en extracción general.",
                        payload_invalido=v,
                    )
                )
                errores_detectados += 1
                continue

            uuid_compuesto, fecha_n, hora_n = _sync_venta_pk_parts(sucursal.nombre, v, orden)
            mesero_existente = db.execute(
                select(models.Venta.mesero_codigo, models.Venta.mesero_nombre).where(
                    models.Venta.id == uuid_compuesto
                )
            ).first()
            if mesero_existente is not None:
                kw = _sync_payload_to_venta_kwargs(v)
                cod_p = str(kw.get("mesero_codigo") or "").strip()
                nom_p = str(kw.get("mesero_nombre") or "").strip()
                if cod_p or nom_p:
                    ex_cod = str(mesero_existente[0] or "").strip()
                    ex_nom = str(mesero_existente[1] or "").strip()
                    if not ex_cod and not ex_nom:
                        db.execute(
                            update(models.Venta)
                            .where(models.Venta.id == uuid_compuesto)
                            .values(
                                mesero_codigo=kw.get("mesero_codigo"),
                                mesero_nombre=kw.get("mesero_nombre"),
                            )
                        )
                        mesero_historial_backfill += 1
                continue

            kw = _sync_payload_to_venta_kwargs(v)
            kw["fecha"] = fecha_n
            kw["hora"] = hora_n
            row = _venta_row_dict(uuid_compuesto, sucursal.id, orden, kw)
            if _insert_venta_idempotent(db, row):
                nuevas_inserciones += 1
                db.query(models.VentaTurno).filter(
                    models.VentaTurno.sucursal_id == sucursal.id,
                    models.VentaTurno.orden == orden,
                ).delete(synchronize_session=False)

        if "turno_actual" in payload:
            db.query(models.VentaTurno).filter(models.VentaTurno.sucursal_id == sucursal.id).delete(
                synchronize_session=False
            )
            turno_proc, turno_dupes = _dedupe_turno_por_orden(payload.get("turno_actual") or [])
            if turno_dupes:
                logger.info(
                    "sync %s: turno_actual con %s ORDEN duplicado(s); se conserva la última fila por ORDEN",
                    sucursal.nombre,
                    turno_dupes,
                )
            for v in turno_proc:
                orden_t = str(v.get("orden", "")).strip()
                if not orden_t:
                    db.add(
                        models.LogSync(
                            sucursal_id=sucursal.id,
                            tipo="Error Crítico ORDEN",
                            mensaje="turno_actual: registro sin ORDEN.",
                            payload_invalido=v,
                        )
                    )
                    errores_detectados += 1
                    continue
                tid = f"{sucursal.id}_{orden_t}"
                kw_t = _sync_payload_to_venta_kwargs(v)
                row_t = {
                    "id": tid,
                    "sucursal_id": sucursal.id,
                    "orden": orden_t,
                    "factura": kw_t.get("factura"),
                    "fecha": _sync_normalize_fecha(kw_t.get("fecha")),
                    "hora": _sync_normalize_hora(kw_t.get("hora")),
                    "total_pagado": kw_t.get("total_pagado", 0),
                    "subtotal": kw_t.get("subtotal", 0),
                    "metodo_pago_tarjeta": kw_t.get("metodo_pago_tarjeta", "N/A"),
                    "monto_tarjeta": kw_t.get("monto_tarjeta", 0),
                    "monto_efectivo": kw_t.get("monto_efectivo", 0),
                    "pagos": kw_t.get("pagos"),
                    "mesero_codigo": kw_t.get("mesero_codigo"),
                    "mesero_nombre": kw_t.get("mesero_nombre"),
                    "propinas": kw_t.get("propinas"),
                    "detalles": kw_t.get("detalles", []),
                }
                if _insert_venta_turno_idempotent(db, row_t):
                    turno_filas += 1

        db.commit()
        db.expunge_all()
    except Exception as exc:
        db.rollback()
        db.add(
            models.LogSync(
                sucursal_id=sucursal.id,
                tipo="Error Sync Upload",
                mensaje=str(exc),
                payload_invalido=payload,
            )
        )
        db.commit()
        logger.exception("upload_sync_data falló (sucursal=%s)", sucursal.nombre)
        detail = str(exc)
        if len(detail) > 1200:
            detail = detail[:1200] + "…"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al persistir sync: {detail}",
        ) from exc
    return {
        "status": "ok",
        "nuevas_ventas_historial_insertadas": nuevas_inserciones,
        "logs_huerfanos": errores_detectados,
        "turno_actual_filas": turno_filas,
        "mesero_historial_backfill": mesero_historial_backfill,
        "sucursal": sucursal_nombre,
    }
