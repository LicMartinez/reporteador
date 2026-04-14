-- Índices de rendimiento para consultas del dashboard por rango/sucursal.
-- Idempotente, seguro re-ejecutar.

BEGIN;

CREATE INDEX IF NOT EXISTS ix_ventas_sucursal_fecha ON ventas (sucursal_id, fecha);
CREATE INDEX IF NOT EXISTS ix_ventas_fecha_sucursal ON ventas (fecha, sucursal_id);
CREATE INDEX IF NOT EXISTS ix_ventas_turno_sucursal_fecha ON ventas_turno (sucursal_id, fecha);
CREATE INDEX IF NOT EXISTS ix_ventas_turno_fecha_sucursal ON ventas_turno (fecha, sucursal_id);
CREATE INDEX IF NOT EXISTS ix_ventas_sucursal_orden ON ventas (sucursal_id, orden);
CREATE INDEX IF NOT EXISTS ix_ventas_turno_sucursal_orden ON ventas_turno (sucursal_id, orden);

COMMIT;
