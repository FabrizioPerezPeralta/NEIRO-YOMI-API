import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# Normalize Postgres connection string if provider gives postgres://
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
else:
    # Supabase & PostgreSQL production connection configuration
    # Enforce SSL for remote Supabase connections
    if "sslmode" not in db_url and "localhost" not in db_url and "127.0.0.1" not in db_url:
        connect_args["sslmode"] = "require"

    # If using Supabase Connection Pooler (PgBouncer/Supavisor on port 6543), disable prepared statement cache
    if ":6543" in db_url:
        connect_args["prepare_threshold"] = None

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_size=10,
        max_overflow=20,
        pool_recycle=300,
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
