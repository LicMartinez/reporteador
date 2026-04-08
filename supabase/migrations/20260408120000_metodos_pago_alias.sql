-- Reglas para unificar nombres de métodos de pago por sucursal (Swiss Admin).

CREATE TABLE IF NOT EXISTS metodos_pago_alias (
  id TEXT PRIMARY KEY,
  sucursal_id TEXT NOT NULL REFERENCES sucursales (id) ON DELETE CASCADE,
  alias TEXT NOT NULL,
  alias_norm TEXT NOT NULL,
  nombre_canonico TEXT NOT NULL,
  CONSTRAINT uq_metodo_pago_alias_suc_norm UNIQUE (sucursal_id, alias_norm)
);

CREATE INDEX IF NOT EXISTS ix_metodos_pago_alias_sucursal ON metodos_pago_alias (sucursal_id);
