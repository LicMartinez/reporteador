import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL vía Supabase en producción, o SQLite local para desarrollo.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///../restbar_local.db")

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}
    # Pooler de Supabase / Postgres en la nube suele requerir SSL.
    if "supabase.co" in DATABASE_URL or os.environ.get("DATABASE_SSL", "").lower() in ("1", "true", "yes"):
        connect_args["sslmode"] = "require"

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
