"""
Crea sucursales piloto y un usuario administrador. Ejecutar desde la raíz del repo:

  set PYTHONPATH=.
  python scripts/seed_admin.py

Variables de entorno:
  DATABASE_URL   — misma cadena que el backend (Supabase Postgres recomendado)
  SEED_ADMIN_EMAIL
  SEED_ADMIN_PASSWORD
  SEED_ADMIN_NAME  — opcional
"""
import os
import sys

# Raíz del proyecto en sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sqlalchemy import inspect, text

from backend.database import Base, engine, SessionLocal
from backend import models
from backend.auth_core import hash_password


PILOTO = ["BAR_LOVE", "BOCCA", "SANA_SANA", "PANEM"]


def _ensure_sqlite_usuario_is_admin():
    if not str(engine.url).startswith("sqlite"):
        return
    insp = inspect(engine)
    try:
        cols = [c["name"] for c in insp.get_columns("usuarios")]
    except Exception:
        return
    if "is_admin" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN DEFAULT 0"))


def main():
    email = (os.environ.get("SEED_ADMIN_EMAIL") or "admin@restbar.local").strip().lower()
    password = os.environ.get("SEED_ADMIN_PASSWORD") or "CambiarPassword123!"
    nombre = os.environ.get("SEED_ADMIN_NAME") or "Administrador"

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_usuario_is_admin()
    db = SessionLocal()
    try:
        for nom in PILOTO:
            if not db.query(models.Sucursal).filter(models.Sucursal.nombre == nom).first():
                db.add(models.Sucursal(nombre=nom))
        db.commit()

        existing = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        if existing:
            print(f"Usuario ya existe: {email}")
            return

        user = models.Usuario(
            email=email,
            password_hash=hash_password(password),
            nombre=nombre,
            is_admin=True,
            portal_admin=True,
            # Para admin del portal no aplicamos expiración del dashboard.
            dashboard_access_until=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        for suc in db.query(models.Sucursal).filter(models.Sucursal.nombre.in_(PILOTO)).all():
            exists_link = (
                db.query(models.UsuarioSucursal)
                .filter(
                    models.UsuarioSucursal.usuario_id == user.id,
                    models.UsuarioSucursal.sucursal_id == suc.id,
                )
                .first()
            )
            if not exists_link:
                db.add(
                    models.UsuarioSucursal(
                        usuario_id=user.id,
                        sucursal_id=suc.id,
                        rol=models.PermisoNivel.ADMIN.value,
                    )
                )
        db.commit()
        print(f"Admin creado: {email} (cambiar contraseña en producción)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
