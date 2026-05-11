import logging
import os
from sqlalchemy import create_engine, inspect, text

logger = logging.getLogger(__name__)
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL vía Supabase en producción, o SQLite local para desarrollo.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///../restbar_local.db")

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
else:
    connect_args = {}
    # Supabase (directo db.*.supabase.co o pooler *.pooler.supabase.com) requiere SSL.
    url_lower = DATABASE_URL.lower()
    if (
        "supabase.co" in url_lower
        or "pooler.supabase.com" in url_lower
        or os.environ.get("DATABASE_SSL", "").lower() in ("1", "true", "yes")
    ):
        connect_args["sslmode"] = "require"

    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_schema_columns() -> None:
    """
    Añade columnas nuevas en instalaciones existentes (create_all no altera tablas).
    Propaga excepciones: el arranque de la app las captura y loguea; /sync/upload las reintenta
    para que un fallo transitorio o un despliegue sin migración SQL manual se autocorrija cuando sea posible.
    """
    insp = inspect(engine)
    names = insp.get_table_names()
    is_sqlite = engine.dialect.name == "sqlite"
    pagos_type = "TEXT" if is_sqlite else "JSONB"
    propinas_type = "REAL" if is_sqlite else "DOUBLE PRECISION"

    def statements_for_table(table: str) -> list[str]:
        if table not in names:
            return []
        cols = {c["name"] for c in insp.get_columns(table)}
        out: list[str] = []
        if "pagos" not in cols:
            out.append(f"ALTER TABLE {table} ADD COLUMN pagos {pagos_type}")
        if "mesero_codigo" not in cols:
            out.append(f"ALTER TABLE {table} ADD COLUMN mesero_codigo VARCHAR")
        if "mesero_nombre" not in cols:
            out.append(f"ALTER TABLE {table} ADD COLUMN mesero_nombre VARCHAR")
        if "propinas" not in cols:
            out.append(f"ALTER TABLE {table} ADD COLUMN propinas {propinas_type}")
        if "fecha_operacion" not in cols:
            out.append(f"ALTER TABLE {table} ADD COLUMN fecha_operacion VARCHAR")
        return out

    for tbl in ("ventas", "ventas_turno"):
        for sql in statements_for_table(tbl):
            with engine.begin() as conn:
                conn.execute(text(sql))

    # Crear índice en fecha_operacion si no existe (para queries rápidas por día de negocio)
    if engine.dialect.name == "postgresql":
        for tbl in ("ventas", "ventas_turno"):
            if tbl in names:
                idx_name = f"ix_{tbl}_fecha_operacion"
                existing_indexes = {idx["name"] for idx in insp.get_indexes(tbl)}
                if idx_name not in existing_indexes:
                    cols = {c["name"] for c in insp.get_columns(tbl)}
                    if "fecha_operacion" in cols:
                        with engine.begin() as conn:
                            conn.execute(text(
                                f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl} (fecha_operacion)"
                            ))

    if "sucursales" in names:
        scols = {c["name"] for c in insp.get_columns("sucursales")}
        if "hora_corte_operativa_minutos" not in scols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE sucursales ADD COLUMN hora_corte_operativa_minutos INTEGER"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
