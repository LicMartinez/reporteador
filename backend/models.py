import uuid
import datetime
import enum
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from .database import Base

class PermisoNivel(enum.Enum):
    ADMIN = "admin"
    VISOR = "visor"

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nombre = Column(String)
    # Admin del dashboard (vista global). Históricamente usado en el MVP.
    is_admin = Column(Boolean, default=False)

    # Admin del portal Swiss Tools Dashboard Admon.
    portal_admin = Column(Boolean, default=False)

    # Expiración del acceso al dashboard para usuarios estándar (no portal_admin).
    dashboard_access_until = Column(DateTime, nullable=True)
    last_dashboard_access_at = Column(DateTime, nullable=True)

    # Catálogo maestro asignado para fuzzy/mapeo de productos.
    catalogo_maestro_id = Column(String, ForeignKey("catalogos_maestros.id"), nullable=True)
    catalogo_maestro = relationship("CatalogoMaestro", back_populates="usuarios")
    
    # Mapeo Multi-Inquilino (Multi-Tenant Access)
    sucursales_acceso = relationship("UsuarioSucursal", back_populates="usuario")

class Sucursal(Base):
    __tablename__ = "sucursales"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, unique=True, index=True, nullable=False) # ej: BAR_LOVE, SUC_PRUEBA
    sync_paused = Column(Boolean, default=False)
    ultimo_checkpoint_historico = Column(DateTime, nullable=True) # Para Tracker Incremental

    # Credencial para el agent de sincronización (validar quién puede subir datos).
    sync_password_hash = Column(String, nullable=True)
    last_connection_at = Column(DateTime, nullable=True)
    
    ventas = relationship("Venta", back_populates="sucursal")
    ventas_turno = relationship("VentaTurno", back_populates="sucursal", cascade="all, delete-orphan")
    logs = relationship("LogSync", back_populates="sucursal")
    usuarios_acceso = relationship("UsuarioSucursal", back_populates="sucursal")


class CatalogoMaestro(Base):
    __tablename__ = "catalogos_maestros"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, unique=True, nullable=False)

    # Relación con usuarios que usan este catálogo
    usuarios = relationship("Usuario", back_populates="catalogo_maestro")

    sucursales_comparten = relationship(
        "CatalogoMaestroSucursal", back_populates="catalogo", cascade="all, delete-orphan"
    )

    productos = relationship(
        "CatalogoMaestroProducto", back_populates="catalogo", cascade="all, delete-orphan"
    )


class CatalogoMaestroSucursal(Base):
    __tablename__ = "catalogos_maestros_sucursales"

    catalogo_id = Column(String, ForeignKey("catalogos_maestros.id"), primary_key=True)
    sucursal_id = Column(String, ForeignKey("sucursales.id"), primary_key=True)

    catalogo = relationship("CatalogoMaestro", back_populates="sucursales_comparten")
    sucursal = relationship("Sucursal", viewonly=True)


class CatalogoMaestroProducto(Base):
    __tablename__ = "catalogos_maestros_productos"

    catalogo_id = Column(String, ForeignKey("catalogos_maestros.id"), primary_key=True)
    nombre_maestro = Column(String, primary_key=True)
    alias_local = Column(String, primary_key=True)

    catalogo = relationship("CatalogoMaestro", back_populates="productos")

class UsuarioSucursal(Base):
    __tablename__ = "usuario_sucursales"
    
    usuario_id = Column(String, ForeignKey("usuarios.id"), primary_key=True)
    sucursal_id = Column(String, ForeignKey("sucursales.id"), primary_key=True)
    rol = Column(String, default=PermisoNivel.VISOR.value)
    
    usuario = relationship("Usuario", back_populates="sucursales_acceso")
    sucursal = relationship("Sucursal", back_populates="usuarios_acceso")

class Venta(Base):
    """
    Consolidado de ventas desde (FACTURA1/2).
    La llave primaria evita inserción duplicada cruzando UUIDs compuestos.
    """
    __tablename__ = "ventas"
    
    id = Column(String, primary_key=True, index=True) # UUID = SUCURSAL + FECHA + HORA + ORDEN
    sucursal_id = Column(String, ForeignKey("sucursales.id"), index=True)
    orden = Column(String, index=True)
    factura = Column(String)
    fecha = Column(String, index=True) # ISO "2026-03-24"
    hora = Column(String)
    total_pagado = Column(Float)
    subtotal = Column(Float)
    metodo_pago_tarjeta = Column(String)
    monto_tarjeta = Column(Float)
    monto_efectivo = Column(Float)
    # Desglose de pagos: [{"name": str, "amount": float, "kind": "efectivo"|"tarjeta"|"otro"}]
    pagos = Column(JSON, nullable=True)
    mesero_codigo = Column(String, nullable=True)
    mesero_nombre = Column(String, nullable=True)
    propinas = Column(Float, nullable=True)

    # Json para renglones (productos)
    detalles = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sucursal = relationship("Sucursal", back_populates="ventas")


class VentaTurno(Base):
    """
    Tickets del turno en curso (FACTURA1T/2T). Se reemplazan en cada sync con `turno_actual`.
    No deben duplicar órdenes ya persistidos en `ventas` (histórico).
    """

    __tablename__ = "ventas_turno"

    id = Column(String, primary_key=True, index=True)
    sucursal_id = Column(String, ForeignKey("sucursales.id"), index=True, nullable=False)
    orden = Column(String, index=True, nullable=False)
    factura = Column(String)
    fecha = Column(String, index=True)
    hora = Column(String)
    total_pagado = Column(Float)
    subtotal = Column(Float)
    metodo_pago_tarjeta = Column(String)
    monto_tarjeta = Column(Float)
    monto_efectivo = Column(Float)
    pagos = Column(JSON, nullable=True)
    mesero_codigo = Column(String, nullable=True)
    mesero_nombre = Column(String, nullable=True)
    propinas = Column(Float, nullable=True)
    detalles = Column(JSON, default=list)

    sucursal = relationship("Sucursal", back_populates="ventas_turno")

class LogSync(Base):
    __tablename__ = "logs_sync"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sucursal_id = Column(String, ForeignKey("sucursales.id"))
    tipo = Column(String) # Módulo (Ej. Error, Limpieza, Integridad)
    mensaje = Column(String)
    payload_invalido = Column(JSON, nullable=True) # Datos Huérfanos
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)
    
    sucursal = relationship("Sucursal", back_populates="logs")
