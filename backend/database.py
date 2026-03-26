import os
from sqlalchemy import create_engine
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
