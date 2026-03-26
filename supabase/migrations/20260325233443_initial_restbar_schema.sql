-- Esquema RestBar Dashboard (alineado con backend SQLAlchemy)
-- Proyecto Supabase: restbar-reporteador-mvp
-- Aplicado vía MCP; mantener en sync con backend/models.py

CREATE TABLE usuarios (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  nombre TEXT,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE UNIQUE INDEX ix_usuarios_email ON usuarios (email);

CREATE TABLE sucursales (
  id TEXT PRIMARY KEY,
  nombre TEXT NOT NULL,
  sync_paused BOOLEAN NOT NULL DEFAULT FALSE,
  ultimo_checkpoint_historico TIMESTAMPTZ NULL
);
CREATE UNIQUE INDEX ix_sucursales_nombre ON sucursales (nombre);

CREATE TABLE usuario_sucursales (
  usuario_id TEXT NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
  sucursal_id TEXT NOT NULL REFERENCES sucursales (id) ON DELETE CASCADE,
  rol TEXT DEFAULT 'visor',
  PRIMARY KEY (usuario_id, sucursal_id)
);

CREATE TABLE ventas (
  id TEXT PRIMARY KEY,
  sucursal_id TEXT NOT NULL REFERENCES sucursales (id) ON DELETE CASCADE,
  orden TEXT,
  factura TEXT,
  fecha TEXT,
  hora TEXT,
  total_pagado DOUBLE PRECISION,
  subtotal DOUBLE PRECISION,
  metodo_pago_tarjeta TEXT,
  monto_tarjeta DOUBLE PRECISION,
  monto_efectivo DOUBLE PRECISION,
  detalles JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ventas_sucursal_id ON ventas (sucursal_id);
CREATE INDEX ix_ventas_orden ON ventas (orden);
CREATE INDEX ix_ventas_fecha ON ventas (fecha);

CREATE TABLE logs_sync (
  id TEXT PRIMARY KEY,
  sucursal_id TEXT REFERENCES sucursales (id) ON DELETE SET NULL,
  tipo TEXT,
  mensaje TEXT,
  payload_invalido JSONB,
  fecha_registro TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE usuarios IS 'Usuarios del dashboard; is_admin ve todas las sucursales.';
COMMENT ON TABLE sucursales IS 'Sucursales RestBar; nombre coincide con /sync/upload/{nombre}.';
COMMENT ON TABLE ventas IS 'Hechos de venta sincronizados desde FACTURA1/2; id deduplicado sucursal+fecha+hora+orden.';
COMMENT ON TABLE logs_sync IS 'Errores de sync y eventos de mantenimiento.';
