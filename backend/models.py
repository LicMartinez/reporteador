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
    is_admin = Column(Boolean, default=False)
    
    # Mapeo Multi-Inquilino (Multi-Tenant Access)
    sucursales_acceso = relationship("UsuarioSucursal", back_populates="usuario")

class Sucursal(Base):
    __tablename__ = "sucursales"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, unique=True, index=True, nullable=False) # ej: BAR_LOVE, SUC_PRUEBA
    sync_paused = Column(Boolean, default=False)
    ultimo_checkpoint_historico = Column(DateTime, nullable=True) # Para Tracker Incremental
    
    ventas = relationship("Venta", back_populates="sucursal")
    logs = relationship("LogSync", back_populates="sucursal")
    usuarios_acceso = relationship("UsuarioSucursal", back_populates="sucursal")

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
    
    # Json para renglones (productos)
    detalles = Column(JSON, default=list) 
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sucursal = relationship("Sucursal", back_populates="ventas")

class LogSync(Base):
    __tablename__ = "logs_sync"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sucursal_id = Column(String, ForeignKey("sucursales.id"))
    tipo = Column(String) # Módulo (Ej. Error, Limpieza, Integridad)
    mensaje = Column(String)
    payload_invalido = Column(JSON, nullable=True) # Datos Huérfanos
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)
    
    sucursal = relationship("Sucursal", back_populates="logs")
