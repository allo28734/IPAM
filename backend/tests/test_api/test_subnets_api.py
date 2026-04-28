"""
API integration tests for the Subnet endpoints.

These tests verify the full HTTP request/response cycle including
status codes, response schemas, and error handling. They hit the
actual FastAPI routers but use an in-memory test database.
"""


class TestSubnetEndpoints:
    """End-to-end tests for /api/v1/subnets."""

    # ── POST /subnets ───────────────────────────────────────────

    def test_create_subnet_201(self, client):
        resp = client.post("/api/v1/subnets", json={
            "name": "Office LAN",
            "cidr": "10.0.1.0/24",
            "gateway": "10.0.1.1",
            "vlan_id": 100,
            "description": "Main office",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Office LAN"
        assert data["cidr"] == "10.0.1.0/24"
        assert data["id"] is not None

    def test_create_subnet_invalid_cidr_422(self, client):
        resp = client.post("/api/v1/subnets", json={
            "name": "Bad", "cidr": "not-a-cidr",
        })
        assert resp.status_code == 422

    def test_create_subnet_overlap_409(self, client):
        client.post("/api/v1/subnets", json={"name": "A", "cidr": "10.0.1.0/24"})
        resp = client.post("/api/v1/subnets", json={"name": "B", "cidr": "10.0.0.0/16"})
        assert resp.status_code == 409

    def test_create_subnet_bad_gateway_422(self, client):
        resp = client.post("/api/v1/subnets", json={
            "name": "BadGW", "cidr": "10.0.1.0/24", "gateway": "192.168.1.1",
        })
        assert resp.status_code == 422

    # ── GET /subnets ────────────────────────────────────────────

    def test_list_subnets_200(self, client):
        client.post("/api/v1/subnets", json={"name": "A", "cidr": "10.0.1.0/24"})
        client.post("/api/v1/subnets", json={"name": "B", "cidr": "10.0.2.0/24"})

        resp = client.get("/api/v1/subnets")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2

    def test_list_subnets_search(self, client):
        client.post("/api/v1/subnets", json={"name": "Office", "cidr": "10.0.1.0/24"})
        client.post("/api/v1/subnets", json={"name": "Server", "cidr": "10.0.2.0/24"})

        resp = client.get("/api/v1/subnets", params={"search": "office"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    # ── GET /subnets/{id} ───────────────────────────────────────

    def test_get_subnet_200(self, client):
        create_resp = client.post("/api/v1/subnets", json={
            "name": "Test", "cidr": "10.0.1.0/24",
        })
        subnet_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/subnets/{subnet_id}")
        assert resp.status_code == 200
        assert resp.json()["cidr"] == "10.0.1.0/24"

    def test_get_subnet_404(self, client):
        resp = client.get("/api/v1/subnets/999")
        assert resp.status_code == 404

    # ── PUT /subnets/{id} ───────────────────────────────────────

    def test_update_subnet_200(self, client):
        create_resp = client.post("/api/v1/subnets", json={
            "name": "Old", "cidr": "10.0.1.0/24",
        })
        subnet_id = create_resp.json()["id"]

        resp = client.put(f"/api/v1/subnets/{subnet_id}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    def test_update_subnet_404(self, client):
        resp = client.put("/api/v1/subnets/999", json={"name": "Ghost"})
        assert resp.status_code == 404

    # ── DELETE /subnets/{id} ────────────────────────────────────

    def test_delete_subnet_204(self, client):
        create_resp = client.post("/api/v1/subnets", json={
            "name": "ToDelete", "cidr": "10.0.1.0/24",
        })
        subnet_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/subnets/{subnet_id}")
        assert resp.status_code == 204

        # Confirm it's gone
        assert client.get(f"/api/v1/subnets/{subnet_id}").status_code == 404

    def test_delete_subnet_404(self, client):
        resp = client.delete("/api/v1/subnets/999")
        assert resp.status_code == 404

    # ── GET /subnets/{id}/utilization ───────────────────────────

    def test_utilization_200(self, client):
        create_resp = client.post("/api/v1/subnets", json={
            "name": "Test", "cidr": "10.0.1.0/24",
        })
        subnet_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/subnets/{subnet_id}/utilization")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_capacity"] == 254
        assert data["utilization_percent"] == 0.0

    def test_utilization_404(self, client):
        resp = client.get("/api/v1/subnets/999/utilization")
        assert resp.status_code == 404
