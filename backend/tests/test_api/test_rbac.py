import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.models.user import User

def test_readonly_user_rbac(client: TestClient, db):
    # Override the user to be a readonly user
    def override_get_current_user():
        return User(id=2, username="readonly_user", role="readonly")
    
    # Need to update the dependency override in the app associated with the client
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_current_user] = override_get_current_user

    # Test GET subnets (should be 200 OK)
    resp = client.get("/api/v1/subnets")
    assert resp.status_code == 200

    # Test POST subnet (should be 403)
    resp = client.post("/api/v1/subnets", json={
        "name": "Test Subnet",
        "cidr": "10.0.1.0/24",
        "gateway": "10.0.1.1",
    })
    assert resp.status_code == 403

    # Clean up override
    fastapi_app.dependency_overrides.pop(get_current_user)
