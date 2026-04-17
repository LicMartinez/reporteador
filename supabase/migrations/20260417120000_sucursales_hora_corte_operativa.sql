-- Día operativo por sucursal (turnos nocturnos). NULL = comportamiento histórico (solo fecha POS).
ALTER TABLE sucursales
  ADD COLUMN IF NOT EXISTS hora_corte_operativa_minutos INTEGER NULL;

COMMENT ON COLUMN sucursales.hora_corte_operativa_minutos IS
  '0..1439: tickets con hora local < este corte en la misma fecha calendario cuentan en el día operativo anterior.';
