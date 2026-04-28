"""
Database engine, session factory, and declarative Base.

This module is the single source of truth for database connectivity.
All repository classes receive a session via dependency injection —
they never create their own connections.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# SQLite requires check_same_thread=False when used with FastAPI's
# threaded request handling.
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""

    pass


def get_db():
    """
    FastAPI dependency that yields a database session.

    The session is automatically closed after the request completes,
    regardless of whether an exception occurred.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
