"""
Database engine, session factory, and declarative Base.

This module is the single source of truth for database connectivity.
All repository classes receive a session via dependency injection —
they never create their own connections.
"""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, autocommit=False, autoflush=False, expire_on_commit=False)


naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""

    metadata = MetaData(naming_convention=naming_convention)


async def get_db():
    """
    FastAPI dependency that yields a database session.

    The session is automatically closed after the request completes,
    regardless of whether an exception occurred.
    """
    async with SessionLocal() as db:
        yield db
