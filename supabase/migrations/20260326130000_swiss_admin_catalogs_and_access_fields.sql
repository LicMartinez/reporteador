-- Swiss Tools Dashboard Admon (Portal Admin) + Catálogos maestros + expiración de acceso
-- Proyecto: restbar-reporteador-mvp (ref rnxzksljzqjwxzjaaqay)
-- Mantener en sync con backend/models.py y backend/schemas.py

BEGIN;

ALTER TABLE usuarios
  ADD COLUMN portal_admin BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE sucursales
  ADD COLUMN sync_password_hash TEXT NULL,
  ADD COLUMN last_connection_at TIMESTAMPTZ NULL;

CREATE TABLE IF NOT EXISTS catalogos_maestros (
  id TEXT PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS catalogos_maestros_sucursales (
  catalogo_id TEXT NOT NULL REFERENCES catalogos_maestros(id) ON DELETE CASCADE,
  sucursal_id TEXT NOT NULL REFERENCES sucursales(id) ON DELETE CASCADE,
  PRIMARY KEY (catalogo_id, sucursal_id)
);

CREATE TABLE IF NOT EXISTS catalogos_maestros_productos (
  catalogo_id TEXT NOT NULL REFERENCES catalogos_maestros(id) ON DELETE CASCADE,
  nombre_maestro TEXT NOT NULL,
  alias_local TEXT NOT NULL,
  PRIMARY KEY (catalogo_id, nombre_maestro, alias_local)
);

ALTER TABLE usuarios
  ADD COLUMN catalogo_maestro_id TEXT NULL,
  ADD COLUMN dashboard_access_until TIMESTAMPTZ NULL,
  ADD COLUMN last_dashboard_access_at TIMESTAMPTZ NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_usuarios_catalogo_maestro_id'
  ) THEN
    ALTER TABLE usuarios
      ADD CONSTRAINT fk_usuarios_catalogo_maestro_id
      FOREIGN KEY (catalogo_maestro_id)
      REFERENCES catalogos_maestros(id)
      ON DELETE SET NULL;
  END IF;
END
$$;

-- Backfill portal_admin for existing admin users
UPDATE usuarios
SET portal_admin = is_admin
WHERE is_admin = TRUE AND portal_admin = FALSE;

COMMIT;

