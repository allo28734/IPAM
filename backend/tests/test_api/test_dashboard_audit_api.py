"""
API integration tests for Dashboard and Audit endpoints.
"""


class TestDashboardEndpoint:
    """Tests for /api/v1/dashboard/stats."""

    def test_dashboard_stats_empty(self, client):
        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_subnets"] == 0
        assert data["total_ips"] == 0
        assert data["overall_utilization"] == 0.0

    def test_dashboard_stats_with_data(self, client):
        # Create a subnet and assign an IP
        subnet_resp = client.post("/api/v1/subnets", json={
            "name": "Test", "cidr": "10.0.1.0/24",
        })
        subnet_id = subnet_resp.json()["id"]
        client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "10.0.1.10", "status": "assigned",
        })
        client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "10.0.1.11", "status": "reserved",
        })

        resp = client.get("/api/v1/dashboard/stats")
        data = resp.json()
        assert data["total_subnets"] == 1
        assert data["total_ips"] == 2
        assert data["assigned_ips"] == 1
        assert data["reserved_ips"] == 1


class TestAuditEndpoint:
    """Tests for /api/v1/audit."""

    def test_audit_empty(self, client):
        resp = client.get("/api/v1/audit")
        assert resp.status_code == 200
        assert resp.json()["items"] == []
        assert resp.json()["total"] == 0

    def test_audit_after_operations(self, client):
        # Create a subnet (generates audit entry)
        client.post("/api/v1/subnets", json={
            "name": "Audited", "cidr": "10.0.1.0/24",
        })

        resp = client.get("/api/v1/audit")
        data = resp.json()
        assert data["total"] >= 1
        assert any(log["action"] == "created" for log in data["items"])

    def test_audit_filter_by_entity_type(self, client):
        # Create subnet and assign IP
        subnet_resp = client.post("/api/v1/subnets", json={
            "name": "Test", "cidr": "10.0.1.0/24",
        })
        subnet_id = subnet_resp.json()["id"]
        client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "10.0.1.10",
        })

        # Filter audit to subnet entries only
        resp = client.get("/api/v1/audit", params={"entity_type": "subnet"})
        data = resp.json()
        assert all(log["entity_type"] == "subnet" for log in data["items"])

    def test_audit_filter_by_action(self, client):
        subnet_resp = client.post("/api/v1/subnets", json={
            "name": "Test", "cidr": "10.0.1.0/24",
        })
        subnet_id = subnet_resp.json()["id"]
        client.delete(f"/api/v1/subnets/{subnet_id}")

        resp = client.get("/api/v1/audit", params={"action": "deleted"})
        data = resp.json()
        assert all(log["action"] == "deleted" for log in data["items"])


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
