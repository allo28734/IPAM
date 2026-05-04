"""
API-layer tests for SSO endpoints and local login regression.

Verifies:
  1. SSO endpoints return 404 when SSO is not configured.
  2. The /sso/enabled endpoint reports configuration status.
  3. Local login continues to work with SSO code present.
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
    """Provide a TestClient backed by a fresh in-memory database."""
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

    # Seed a test user for login tests
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

    with TestClient(fastapi_app) as client:
        yield client

    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── SSO disabled (default) ─────────────────────────────────────


class TestSSODisabled:
    """When SSO settings are not configured, SSO endpoints are unavailable."""

    def test_sso_enabled_returns_false(self, client):
        """/sso/enabled should report SSO as disabled."""
        response = client.get("/api/v1/auth/sso/enabled")
        assert response.status_code == 200
        assert response.json() == {"sso_enabled": False}

    def test_sso_login_returns_404(self, client):
        """/sso/login should return 404 when not configured."""
        response = client.get(
            "/api/v1/auth/sso/login", follow_redirects=False
        )
        assert response.status_code == 404

    def test_sso_callback_returns_404(self, client):
        """/sso/callback should return 404 when not configured."""
        response = client.get("/api/v1/auth/sso/callback")
        assert response.status_code == 404


# ── Local login regression ─────────────────────────────────────


class TestLocalLoginRegression:
    """Local login must continue to work with SSO code present."""

    def test_local_login_valid_credentials(self, client):
        """POST /auth/token with correct credentials returns JWT."""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "testadmin", "password": "testpassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_local_login_invalid_credentials(self, client):
        """POST /auth/token with wrong credentials returns 401."""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "testadmin", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_me_endpoint_with_local_token(self, client):
        """GET /auth/me with a local JWT returns the user profile."""
        token_resp = client.post(
            "/api/v1/auth/token",
            data={"username": "testadmin", "password": "testpassword123"},
        )
        token = token_resp.json()["access_token"]

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testadmin"
        assert data["role"] == "admin"
