"""SQLAlchemy engine and session configuration."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


def get_database_url() -> str:
    """Build the PostgreSQL URL from environment variables."""

    user = os.getenv("POSTGRES_USER", "bytebrief")
    password = os.getenv("POSTGRES_PASSWORD", "bytebrief")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "bytebrief")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Session:
    """Create a database session."""

    return SessionLocal()
