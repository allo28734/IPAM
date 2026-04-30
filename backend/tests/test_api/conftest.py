"""
Shared fixtures for API integration tests.

Uses FastAPI's TestClient with a test database session
override so API tests hit an in-memory SQLite database.

IMPORTANT: SQLite in-memory databases are per-connection. We use
StaticPool to ensure the same connection is reused across all
sessions, so that tables created by create_all() are visible to
the sessions used in request handlers.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app as fastapi_app

# Ensure all models are imported so Base.metadata is fully populated
import app.models  # noqa: F401


@pytest.fixture(name="client")
def test_client():
    """
    Provide a TestClient backed by a fresh in-memory database.

    Uses StaticPool to guarantee all sessions share the same
    underlying SQLite connection (required for in-memory DBs).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    from app.api.deps import get_current_user
    from app.models.user import User

    def override_get_current_user():
        return User(id=1, username="testadmin", role="admin")

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(fastapi_app) as client:
        yield client

    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
