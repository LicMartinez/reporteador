-- Columna fecha_operacion: día de negocio pre-calculado al momento del sync.
-- Regla: si hora del ticket < corte (default 06:00 AM), fecha_operacion = día anterior.
-- Elimina la necesidad de calcular en runtime con JOINs y regex complejos.
-- Idempotente, seguro re-ejecutar.

BEGIN;

-- Agregar columna a ventas históricas
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS fecha_operacion TEXT;

-- Agregar columna a ventas del turno actual
ALTER TABLE ventas_turno ADD COLUMN IF NOT EXISTS fecha_operacion TEXT;

-- Índices para queries rápidas por día de negocio
CREATE INDEX IF NOT EXISTS ix_ventas_fecha_operacion ON ventas (fecha_operacion);
CREATE INDEX IF NOT EXISTS ix_ventas_turno_fecha_operacion ON ventas_turno (fecha_operacion);

-- Índices compuestos para filtros por sucursal + fecha_operacion (el caso más común del dashboard)
CREATE INDEX IF NOT EXISTS ix_ventas_sucursal_fecha_op ON ventas (sucursal_id, fecha_operacion);
CREATE INDEX IF NOT EXISTS ix_ventas_turno_sucursal_fecha_op ON ventas_turno (sucursal_id, fecha_operacion);

-- Backfill: calcular fecha_operacion para registros existentes.
-- Usa hora_corte_operativa_minutos de la sucursal; si es NULL usa 360 (06:00 AM).
-- Lógica: si minutos_desde_medianoche(hora) < corte → fecha - 1 día.
UPDATE ventas v
SET fecha_operacion = (
  CASE
    WHEN COALESCE(
      CASE WHEN (regexp_match(trim(COALESCE(v.hora, '')), '^([0-9]{1,2}):([0-9]{2})')) IS NOT NULL THEN
        ((regexp_match(trim(COALESCE(v.hora, '')), '^([0-9]{1,2}):([0-9]{2})'))[1])::int * 60
        + ((regexp_match(trim(COALESCE(v.hora, '')), '^([0-9]{1,2}):([0-9]{2})'))[2])::int
      END, 0
    ) < COALESCE(s.hora_corte_operativa_minutos, 360)
    THEN (v.fecha::date - INTERVAL '1 day')::date::text
    ELSE v.fecha
  END
)
FROM sucursales s
WHERE s.id = v.sucursal_id
  AND v.fecha_operacion IS NULL
  AND v.fecha IS NOT NULL
  AND length(v.fecha) >= 10;

UPDATE ventas_turno t
SET fecha_operacion = (
  CASE
    WHEN COALESCE(
      CASE WHEN (regexp_match(trim(COALESCE(t.hora, '')), '^([0-9]{1,2}):([0-9]{2})')) IS NOT NULL THEN
        ((regexp_match(trim(COALESCE(t.hora, '')), '^([0-9]{1,2}):([0-9]{2})'))[1])::int * 60
        + ((regexp_match(trim(COALESCE(t.hora, '')), '^([0-9]{1,2}):([0-9]{2})'))[2])::int
      END, 0
    ) < COALESCE(s.hora_corte_operativa_minutos, 360)
    THEN (t.fecha::date - INTERVAL '1 day')::date::text
    ELSE t.fecha
  END
)
FROM sucursales s
WHERE s.id = t.sucursal_id
  AND t.fecha_operacion IS NULL
  AND t.fecha IS NOT NULL
  AND length(t.fecha) >= 10;

COMMENT ON COLUMN ventas.fecha_operacion IS 'Día de negocio (YYYY-MM-DD). Si hora < corte (default 06:00), es el día anterior al calendario POS.';
COMMENT ON COLUMN ventas_turno.fecha_operacion IS 'Día de negocio (YYYY-MM-DD). Si hora < corte (default 06:00), es el día anterior al calendario POS.';

COMMIT;
