from pydantic import BaseModel, Field
from typing import List, Optional


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class SucursalBrief(BaseModel):
    id: str
    nombre: str
    rol: Optional[str] = None

    class Config:
        from_attributes = True


class UserMe(BaseModel):
    id: str
    email: str
    nombre: Optional[str] = None
    is_admin: bool
    portal_admin: bool
    sucursales: List[SucursalBrief] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserMe


# =========================
# Admin portal (dashboard)
# =========================


class AdminCreateSucursalRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)


class AdminCreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=256)
    nombre: Optional[str] = None
    is_admin: bool = False
    sucursal_ids: List[str] = []


class AdminUserBrief(BaseModel):
    id: str
    email: str
    nombre: Optional[str] = None
    is_admin: bool
    sucursales: List[SucursalBrief] = []


# =========================
# Swiss Tools Dashboard Admon
# =========================


class SwissSucursalBrief(BaseModel):
    id: str
    nombre: str
    last_connection_at: Optional[str] = None

    class Config:
        from_attributes = True


class SwissSucursalLogsItem(BaseModel):
    id: str
    tipo: Optional[str] = None
    mensaje: Optional[str] = None
    fecha_registro: Optional[str] = None
    payload_invalido: Optional[dict] = None

    class Config:
        from_attributes = True


class SwissCatalogoProductoRule(BaseModel):
    nombre_maestro: str
    alias_local: str


class SwissCatalogoBrief(BaseModel):
    id: str
    nombre: str
    sucursal_ids: List[str] = []
    productos_count: int = 0

    class Config:
        from_attributes = True


class SwissCreateCatalogoRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=140)
    sucursal_ids: List[str] = []
    reglas_productos: List[SwissCatalogoProductoRule] = []


class SwissUpdateCatalogoRequest(BaseModel):
    nombre: Optional[str] = None
    sucursal_ids: Optional[List[str]] = None
    reglas_productos: Optional[List[SwissCatalogoProductoRule]] = None


class SwissAdminCreateSucursalRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=140)
    sync_password: str = Field(min_length=6, max_length=256)


class SwissAdminCreateDashboardUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=256)
    nombre: Optional[str] = None
    sucursal_ids: List[str] = []
    dashboard_access_until: Optional[str] = None  # ISO string (se parsea en backend)
    catalogo_maestro_id: Optional[str] = None


class SwissAdminUpdateDashboardUserAccessRequest(BaseModel):
    dashboard_access_until: Optional[str] = None


class SwissAdminUserBrief(BaseModel):
    id: str
    email: str
    nombre: Optional[str] = None
    dashboard_access_until: Optional[str] = None
    last_dashboard_access_at: Optional[str] = None
    catalogo_maestro_id: Optional[str] = None
    sucursales: List[SucursalBrief] = []

    class Config:
        from_attributes = True


class SwissAdminCreatePortalAdminRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=256)
    nombre: Optional[str] = None


class SwissChangePasswordRequest(BaseModel):
    old_password: Optional[str] = None
    new_password: str = Field(min_length=6, max_length=256)


class SwissUpdatePortalAdminRequest(BaseModel):
    email: Optional[str] = None
    nombre: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=6, max_length=256)
