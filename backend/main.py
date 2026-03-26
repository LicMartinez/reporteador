import os
from collections import defaultdict
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session

import logging

from .database import Base, engine, get_db
from . import models
from .etl_matcher import ETLMatcher
from .auth_core import create_access_token, verify_password
from . import schemas
from .deps import get_current_user, verify_sync_api_key

logger = logging.getLogger(__name__)

_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
ALLOWED_ORIGINS = [o.strip() for o in _origins.split(",") if o.strip()]

app = FastAPI(title="RestBar Dashboard API - Core MultiTenant", version="1.3")


@app.on_event("startup")
def _on_startup():
    """Crea tablas si no existen. No mata el proceso si la DB tarda en responder."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("create_all OK — tablas verificadas")
    except Exception as exc:
        logger.error("create_all falló (se reintentará en la primera petición): %s", exc)

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
        sucursales=sucursales,
    )


@app.get("/")
def home():
    return {"status": "ok", "message": "RestBar Sync API Running"}


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


@app.get("/dashboard/resumen", tags=["Dashboard"])
def dashboard_resumen(
    fecha_desde: str,
    fecha_hasta: str,
    sucursal_id: Optional[str] = None,
    user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    KPIs y series para el dashboard. Admin ve todas las sucursales; visor solo las asignadas en usuario_sucursales.
    """
    q = db.query(models.Venta).join(models.Sucursal, models.Venta.sucursal_id == models.Sucursal.id)

    if not user.is_admin:
        allowed_ids = [
            row.sucursal_id
            for row in db.query(models.UsuarioSucursal)
            .filter(models.UsuarioSucursal.usuario_id == user.id)
            .all()
        ]
        if not allowed_ids:
            return {
                "total_ingresos": 0.0,
                "num_tickets": 0,
                "ticket_promedio": 0.0,
                "total_efectivo": 0.0,
                "total_tarjeta": 0.0,
                "por_hora": [],
                "por_metodo": [],
            }
        q = q.filter(models.Venta.sucursal_id.in_(allowed_ids))

    if sucursal_id:
        q = q.filter(models.Venta.sucursal_id == sucursal_id)

    q = q.filter(models.Venta.fecha >= fecha_desde, models.Venta.fecha <= fecha_hasta)

    ventas: List[models.Venta] = q.all()
    if not ventas:
        return {
            "total_ingresos": 0.0,
            "num_tickets": 0,
            "ticket_promedio": 0.0,
            "total_efectivo": 0.0,
            "total_tarjeta": 0.0,
            "por_hora": [],
            "por_metodo": [],
        }

    total_ingresos = sum(v.total_pagado or 0 for v in ventas)
    num = len(ventas)
    total_efectivo = sum(v.monto_efectivo or 0 for v in ventas)
    total_tarjeta = sum(v.monto_tarjeta or 0 for v in ventas)

    por_hora: dict[str, float] = defaultdict(float)
    for v in ventas:
        h = (v.hora or "").strip()[:5] or "00:00"
        por_hora[h] += float(v.total_pagado or 0)

    metodo_map: dict[str, float] = defaultdict(float)
    for v in ventas:
        label = (v.metodo_pago_tarjeta or "N/A").strip() or "N/A"
        metodo_map[label] += float(v.monto_tarjeta or 0)
    metodo_map["Efectivo"] = total_efectivo

    hora_sorted = sorted(por_hora.keys())
    por_hora_list = [{"name": f"{h}", "ventas": round(por_hora[h], 2)} for h in hora_sorted]
    por_metodo = [{"name": k, "amount": round(metodo_map[k], 2)} for k in sorted(metodo_map, key=lambda x: -metodo_map[x])]

    return {
        "total_ingresos": round(total_ingresos, 2),
        "num_tickets": num,
        "ticket_promedio": round(total_ingresos / num, 2) if num else 0.0,
        "total_efectivo": round(total_efectivo, 2),
        "total_tarjeta": round(total_tarjeta, 2),
        "por_hora": por_hora_list,
        "por_metodo": por_metodo[:12],
    }


@app.get("/dashboard/sucursales", tags=["Dashboard"])
def list_sucursales_for_filter(
    user: models.Usuario = Depends(get_current_user),
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
def limpieza_reset(sucursal_nombre: str, fecha_inicio: str = None, fecha_fin: str = None, db: Session = Depends(get_db)):
    sucursal = db.query(models.Sucursal).filter(models.Sucursal.nombre == sucursal_nombre).first()
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no registrada")

    query = db.query(models.Venta).filter(models.Venta.sucursal_id == sucursal.id)
    if fecha_inicio and fecha_fin:
        query = query.filter(models.Venta.fecha.between(fecha_inicio, fecha_fin))

    borrados = query.delete()

    sucursal.ultimo_checkpoint_historico = None

    log = models.LogSync(
        sucursal_id=sucursal.id,
        tipo="Limpieza",
        mensaje=f"Borrado manual de {borrados} ventas. Checkpoint reseteado. Rango: {fecha_inicio}-{fecha_fin}",
    )
    db.add(log)
    db.commit()

    return {"status": "Limpiado", "registros_retirados": borrados}


# ================================
# ENDPOINT FASE 4: CATÁLOGO E INTELIGENCIA (Tarea 4.1, 4.2, 4.3)
# ================================
@app.get("/admin/export/top10", tags=["Reportes"])
def exportar_top_10_csv(db: Session = Depends(get_db)):
    etl = ETLMatcher(db)
    csv_content = etl.export_top10_to_csv()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=top10_platillos_consolidado.csv"},
    )


# ================================
# ENDPOINT INGESTA SYNC AGENT (Tarea 2.4/2.1)
# ================================
@app.post("/sync/upload/{sucursal_nombre}", tags=["Sincronización"])
def upload_sync_data(
    sucursal_nombre: str,
    payload: dict,
    db: Session = Depends(get_db),
    _: None = Depends(verify_sync_api_key),
):
    """Recepción del agente en cada PC. Protegido con X-API-Key si SYNC_API_KEY está definida."""
    sucursal = db.query(models.Sucursal).filter(models.Sucursal.nombre == sucursal_nombre).first()

    if not sucursal:
        sucursal = models.Sucursal(nombre=sucursal_nombre.upper())
        db.add(sucursal)
        db.commit()
        db.refresh(sucursal)

    if sucursal.sync_paused:
        raise HTTPException(status_code=503, detail="Sync pausado para esta sucursal.")

    historial = payload.get("historial", [])
    nuevas_inserciones = 0
    errores_detectados = 0

    for v in historial:
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

        uuid_compuesto = f"{sucursal.nombre}_{v.get('fecha')}_{v.get('hora')}_{orden}"

        existe = db.query(models.Venta).filter(models.Venta.id == uuid_compuesto).first()
        if not existe:
            db_venta = models.Venta(
                id=uuid_compuesto,
                sucursal_id=sucursal.id,
                orden=orden,
                factura=v.get("factura"),
                fecha=v.get("fecha"),
                hora=v.get("hora"),
                total_pagado=v.get("total_pagado", 0),
                subtotal=v.get("subtotal", 0),
                metodo_pago_tarjeta=v.get("metodo_pago_tarjeta", "N/A"),
                monto_tarjeta=v.get("monto_tarjeta", 0),
                monto_efectivo=v.get("monto_efectivo", 0),
                detalles=v.get("detalles", []),
            )
            db.add(db_venta)
            nuevas_inserciones += 1

    db.commit()
    return {
        "status": "ok",
        "nuevas_ventas_historial_insertadas": nuevas_inserciones,
        "logs_huerfanos": errores_detectados,
        "sucursal": sucursal_nombre,
    }
