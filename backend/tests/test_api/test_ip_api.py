"""
API integration tests for the IP Address endpoints.

These tests verify the full HTTP request/response cycle for
IP assignment, auto-allocation, update, release, and deletion.
"""

import pytest


@pytest.fixture(name="subnet_id")
def create_subnet(client):
    """Create a subnet and return its ID for IP tests."""
    resp = client.post("/api/v1/subnets", json={
        "name": "Test Subnet",
        "cidr": "10.0.1.0/24",
        "gateway": "10.0.1.1",
    })
    return resp.json()["id"]


class TestIPAddressEndpoints:
    """End-to-end tests for IP address API endpoints."""

    # ── POST /subnets/{id}/ips ──────────────────────────────────

    def test_assign_ip_201(self, client, subnet_id):
        resp = client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "10.0.1.10",
            "status": "assigned",
            "hostname": "web-01",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["address"] == "10.0.1.10"
        assert data["status"] == "assigned"

    def test_assign_ip_invalid_address_422(self, client, subnet_id):
        resp = client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "not-an-ip",
        })
        assert resp.status_code == 422

    def test_assign_ip_outside_subnet_422(self, client, subnet_id):
        resp = client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "192.168.1.10",
        })
        assert resp.status_code == 422

    def test_assign_ip_duplicate_409(self, client, subnet_id):
        client.post(f"/api/v1/subnets/{subnet_id}/ips", json={"address": "10.0.1.10"})
        resp = client.post(f"/api/v1/subnets/{subnet_id}/ips", json={"address": "10.0.1.10"})
        assert resp.status_code == 409

    def test_assign_ip_nonexistent_subnet_404(self, client):
        resp = client.post("/api/v1/subnets/999/ips", json={"address": "10.0.1.10"})
        assert resp.status_code == 404

    # ── POST /subnets/{id}/ips/next-available ───────────────────

    def test_allocate_next_201(self, client, subnet_id):
        resp = client.post(f"/api/v1/subnets/{subnet_id}/ips/next-available", json={
            "hostname": "auto-host",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["address"] == "10.0.1.2"  # .1 is gateway
        assert data["hostname"] == "auto-host"

    def test_allocate_next_skips_used(self, client, subnet_id):
        # Assign .2 manually
        client.post(f"/api/v1/subnets/{subnet_id}/ips", json={"address": "10.0.1.2"})

        resp = client.post(f"/api/v1/subnets/{subnet_id}/ips/next-available", json={})
        assert resp.status_code == 201
        assert resp.json()["address"] == "10.0.1.3"

    # ── GET /subnets/{id}/ips ───────────────────────────────────

    def test_list_ips_200(self, client, subnet_id):
        client.post(f"/api/v1/subnets/{subnet_id}/ips", json={"address": "10.0.1.10"})
        client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "10.0.1.11", "status": "reserved",
        })

        resp = client.get(f"/api/v1/subnets/{subnet_id}/ips")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2

    def test_list_ips_filter_by_status(self, client, subnet_id):
        client.post(f"/api/v1/subnets/{subnet_id}/ips", json={"address": "10.0.1.10"})
        client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "10.0.1.11", "status": "reserved",
        })

        resp = client.get(f"/api/v1/subnets/{subnet_id}/ips", params={"status": "reserved"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    # ── PUT /ips/{id} ───────────────────────────────────────────

    def test_update_ip_200(self, client, subnet_id):
        create_resp = client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "10.0.1.10",
        })
        ip_id = create_resp.json()["id"]

        resp = client.put(f"/api/v1/ips/{ip_id}", json={"hostname": "new-host"})
        assert resp.status_code == 200
        assert resp.json()["hostname"] == "new-host"

    def test_update_ip_404(self, client):
        resp = client.put("/api/v1/ips/999", json={"hostname": "ghost"})
        assert resp.status_code == 404

    # ── POST /ips/{id}/release ──────────────────────────────────

    def test_release_ip_200(self, client, subnet_id):
        create_resp = client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "10.0.1.10", "hostname": "web-01",
        })
        ip_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/ips/{ip_id}/release")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "available"
        assert data["hostname"] is None

    def test_release_ip_404(self, client):
        resp = client.post("/api/v1/ips/999/release")
        assert resp.status_code == 404

    # ── DELETE /ips/{id} ────────────────────────────────────────

    def test_delete_ip_204(self, client, subnet_id):
        create_resp = client.post(f"/api/v1/subnets/{subnet_id}/ips", json={
            "address": "10.0.1.10",
        })
        ip_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/ips/{ip_id}")
        assert resp.status_code == 204

    def test_delete_ip_404(self, client):
        resp = client.delete("/api/v1/ips/999")
        assert resp.status_code == 404
