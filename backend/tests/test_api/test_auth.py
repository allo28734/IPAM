"""
Auth API integration tests.

Verifies that:
  1. Unauthenticated requests to protected endpoints return 401.
  2. The /token endpoint returns a valid JWT for correct credentials.
  3. Authenticated requests with a valid JWT succeed.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app as fastapi_app
from app.models.user import User
from app.services.auth_service import hash_password

# Ensure all models are imported so Base.metadata is fully populated
import app.models  # noqa: F401


@pytest.fixture(name="client")
def test_client():
    """
    Provide a TestClient backed by a fresh in-memory database.
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

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as client:
        yield client

    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(name="test_user_db")
def seed_test_user():
    """
    Seed a test user into the database and return credentials.

    Returns a tuple of (engine, username, password).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create a test user
    session = TestingSession()
    user = User(
        username="testadmin",
        email="test@ipam.local",
        hashed_password=hash_password("testpassword123"),
        role="admin",
    )
    session.add(user)
    session.commit()
    session.close()

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as client:
        yield client

    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── Test: Unauthenticated access is denied ─────────────────────


class TestUnauthenticatedAccess:
    """Protected endpoints must return 401 without a valid token."""

    def test_subnets_returns_401(self, client):
        """GET /api/v1/subnets without a token must return 401."""
        response = client.get("/api/v1/subnets")
        assert response.status_code == 401

    def test_dashboard_returns_401(self, client):
        """GET /api/v1/dashboard/stats without a token must return 401."""
        response = client.get("/api/v1/dashboard/stats")
        assert response.status_code == 401

    def test_audit_returns_401(self, client):
        """GET /api/v1/audit without a token must return 401."""
        response = client.get("/api/v1/audit")
        assert response.status_code == 401


# ── Test: Token endpoint ───────────────────────────────────────


class TestTokenEndpoint:
    """The /auth/token endpoint must issue JWTs for valid credentials."""

    def test_login_invalid_credentials(self, client):
        """POST /auth/token with wrong credentials must return 401."""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "nobody", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_valid_credentials(self, test_user_db):
        """POST /auth/token with correct credentials must return a JWT."""
        response = test_user_db.post(
            "/api/v1/auth/token",
            data={"username": "testadmin", "password": "testpassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


# ── Test: Authenticated access succeeds ────────────────────────


class TestAuthenticatedAccess:
    """Protected endpoints must succeed with a valid JWT."""

    def test_subnets_with_token(self, test_user_db):
        """GET /api/v1/subnets with a valid token must return 200."""
        # First, get a token
        token_response = test_user_db.post(
            "/api/v1/auth/token",
            data={"username": "testadmin", "password": "testpassword123"},
        )
        token = token_response.json()["access_token"]

        # Now make an authenticated request
        response = test_user_db.get(
            "/api/v1/subnets",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_me_endpoint(self, test_user_db):
        """GET /auth/me must return the current user's profile."""
        token_response = test_user_db.post(
            "/api/v1/auth/token",
            data={"username": "testadmin", "password": "testpassword123"},
        )
        token = token_response.json()["access_token"]

        response = test_user_db.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testadmin"
        assert data["role"] == "admin"
        assert "hashed_password" not in data
