-- Sync agent + dashboard: columnas en ventas histórico y tabla ventas_turno (FACTURA1T/2T).
-- Alineado con backend/models.py (Venta, VentaTurno) y payload de agent_sync.py.
-- Idempotente: seguro re-ejecutar.

BEGIN;

ALTER TABLE ventas ADD COLUMN IF NOT EXISTS pagos JSONB;
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS mesero_codigo TEXT;
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS mesero_nombre TEXT;

CREATE TABLE IF NOT EXISTS ventas_turno (
  id TEXT PRIMARY KEY,
  sucursal_id TEXT NOT NULL REFERENCES sucursales (id) ON DELETE CASCADE,
  orden TEXT NOT NULL,
  factura TEXT,
  fecha TEXT,
  hora TEXT,
  total_pagado DOUBLE PRECISION,
  subtotal DOUBLE PRECISION,
  metodo_pago_tarjeta TEXT,
  monto_tarjeta DOUBLE PRECISION,
  monto_efectivo DOUBLE PRECISION,
  pagos JSONB,
  mesero_codigo TEXT,
  mesero_nombre TEXT,
  detalles JSONB NOT NULL DEFAULT '[]'::jsonb
);

ALTER TABLE ventas_turno ADD COLUMN IF NOT EXISTS pagos JSONB;
ALTER TABLE ventas_turno ADD COLUMN IF NOT EXISTS mesero_codigo TEXT;
ALTER TABLE ventas_turno ADD COLUMN IF NOT EXISTS mesero_nombre TEXT;

CREATE INDEX IF NOT EXISTS ix_ventas_turno_sucursal_id ON ventas_turno (sucursal_id);
CREATE INDEX IF NOT EXISTS ix_ventas_turno_orden ON ventas_turno (orden);
CREATE INDEX IF NOT EXISTS ix_ventas_turno_fecha ON ventas_turno (fecha);

COMMENT ON TABLE ventas_turno IS 'Tickets del turno en curso; reemplazados en cada POST /sync/upload cuando viene turno_actual.';

COMMIT;
