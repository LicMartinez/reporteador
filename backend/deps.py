import os
from datetime import datetime, timezone
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .auth_core import decode_token

security = HTTPBearer(auto_error=False)


def verify_sync_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    expected = os.environ.get("SYNC_API_KEY")
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key de sincronización inválida o ausente (header X-API-Key).",
        )


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> models.Usuario:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user = db.query(models.Usuario).filter(models.Usuario.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


def get_current_user_dashboard(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """
    Acceso al dashboard:
    - `portal_admin` siempre tiene acceso.
    - Usuarios estándar se bloquean si `dashboard_access_until` ya venció.
    """
    user = get_current_user(creds=creds, db=db)

    if user.portal_admin:
        return user

    if user.dashboard_access_until is not None:
        now = datetime.now(timezone.utc)
        # SQLAlchemy puede devolver naive/aware según driver; normalizamos a UTC naive.
        if hasattr(user.dashboard_access_until, "tzinfo") and user.dashboard_access_until.tzinfo is None:
            # Asumimos que el valor fue guardado en UTC.
            user_dashboard_until = user.dashboard_access_until.replace(tzinfo=timezone.utc)
        else:
            user_dashboard_until = user.dashboard_access_until

        if user_dashboard_until and now > user_dashboard_until:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso al dashboard vencido")

    # Registrar último acceso (mejor effort, no debe romper el flujo).
    try:
        user.last_dashboard_access_at = datetime.now(timezone.utc)
        db.add(user)
        db.commit()
    except Exception:
        db.rollback()

    return user
