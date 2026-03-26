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
    sucursales: List[SucursalBrief] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserMe
