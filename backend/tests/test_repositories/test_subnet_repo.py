"""
Tests for SubnetRepository — Data Access Layer.

These tests verify that the repository correctly performs CRUD
operations and subnet-specific queries against the database.
Business logic (e.g., overlap detection) is NOT tested here —
that belongs in the service layer tests.
"""

import pytest

from app.models.subnet import Subnet
from app.repositories.subnet_repo import SubnetRepository


class TestSubnetRepository:
    """Test suite for SubnetRepository CRUD and query operations."""

    # ── Create ──────────────────────────────────────────────────

    def test_create_subnet(self, db):
        """Creating a subnet persists it and assigns an ID."""
        repo = SubnetRepository(db)
        subnet = Subnet(name="Office LAN", cidr="10.0.1.0/24", gateway="10.0.1.1")

        created = repo.create(subnet)

        assert created.id is not None
        assert created.name == "Office LAN"
        assert created.cidr == "10.0.1.0/24"
        assert created.gateway == "10.0.1.1"
        assert created.created_at is not None

    def test_create_subnet_with_optional_fields(self, db):
        """Optional fields (vlan_id, description) can be set."""
        repo = SubnetRepository(db)
        subnet = Subnet(
            name="Server VLAN",
            cidr="192.168.10.0/24",
            gateway="192.168.10.1",
            vlan_id=100,
            description="Production servers",
        )

        created = repo.create(subnet)

        assert created.vlan_id == 100
        assert created.description == "Production servers"

    # ── Read ────────────────────────────────────────────────────

    def test_get_by_id(self, db):
        """Retrieving a subnet by ID returns the correct record."""
        repo = SubnetRepository(db)
        subnet = repo.create(Subnet(name="Test", cidr="10.0.2.0/24"))

        found = repo.get_by_id(subnet.id)

        assert found is not None
        assert found.id == subnet.id
        assert found.cidr == "10.0.2.0/24"

    def test_get_by_id_not_found(self, db):
        """Querying a non-existent ID returns None."""
        repo = SubnetRepository(db)

        assert repo.get_by_id(999) is None

    def test_get_by_cidr(self, db):
        """Looking up a subnet by CIDR returns the matching record."""
        repo = SubnetRepository(db)
        repo.create(Subnet(name="LAN-A", cidr="10.0.3.0/24"))

        found = repo.get_by_cidr("10.0.3.0/24")

        assert found is not None
        assert found.name == "LAN-A"

    def test_get_by_cidr_not_found(self, db):
        """CIDR lookup returns None when no match exists."""
        repo = SubnetRepository(db)

        assert repo.get_by_cidr("172.16.0.0/16") is None

    def test_get_by_name(self, db):
        """Looking up a subnet by name returns the matching record."""
        repo = SubnetRepository(db)
        repo.create(Subnet(name="DMZ", cidr="10.0.4.0/24"))

        found = repo.get_by_name("DMZ")

        assert found is not None
        assert found.cidr == "10.0.4.0/24"

    def test_get_all(self, db):
        """get_all returns all subnets with pagination."""
        repo = SubnetRepository(db)
        repo.create(Subnet(name="A", cidr="10.0.1.0/24"))
        repo.create(Subnet(name="B", cidr="10.0.2.0/24"))
        repo.create(Subnet(name="C", cidr="10.0.3.0/24"))

        # Fetch all
        all_subnets = repo.get_all()
        assert len(all_subnets) == 3

        # Fetch with pagination
        page = repo.get_all(skip=1, limit=1)
        assert len(page) == 1
        assert page[0].name == "B"

    def test_count(self, db):
        """count() returns the total number of subnets."""
        repo = SubnetRepository(db)
        assert repo.count() == 0

        repo.create(Subnet(name="A", cidr="10.0.1.0/24"))
        repo.create(Subnet(name="B", cidr="10.0.2.0/24"))

        assert repo.count() == 2

    # ── Search ──────────────────────────────────────────────────

    def test_search_by_name(self, db):
        """Search matches partial subnet names (case-insensitive)."""
        repo = SubnetRepository(db)
        repo.create(Subnet(name="Office LAN", cidr="10.0.1.0/24"))
        repo.create(Subnet(name="Server Room", cidr="10.0.2.0/24"))

        results = repo.search("office")

        assert len(results) == 1
        assert results[0].name == "Office LAN"

    def test_search_by_cidr(self, db):
        """Search matches partial CIDR strings."""
        repo = SubnetRepository(db)
        repo.create(Subnet(name="A", cidr="10.0.1.0/24"))
        repo.create(Subnet(name="B", cidr="192.168.1.0/24"))

        results = repo.search("192.168")

        assert len(results) == 1
        assert results[0].name == "B"

    def test_search_no_results(self, db):
        """Search returns empty list when no matches found."""
        repo = SubnetRepository(db)
        repo.create(Subnet(name="A", cidr="10.0.1.0/24"))

        results = repo.search("nonexistent")

        assert len(results) == 0

    # ── Get all CIDRs ──────────────────────────────────────────

    def test_get_all_cidrs(self, db):
        """get_all_cidrs returns a plain list of CIDR strings."""
        repo = SubnetRepository(db)
        repo.create(Subnet(name="A", cidr="10.0.1.0/24"))
        repo.create(Subnet(name="B", cidr="172.16.0.0/16"))

        cidrs = repo.get_all_cidrs()

        assert set(cidrs) == {"10.0.1.0/24", "172.16.0.0/16"}

    # ── Update ──────────────────────────────────────────────────

    def test_update_subnet(self, db):
        """Updating a subnet modifies only the specified fields."""
        repo = SubnetRepository(db)
        subnet = repo.create(Subnet(name="Old Name", cidr="10.0.1.0/24"))

        updated = repo.update(subnet, {"name": "New Name", "description": "Updated"})

        assert updated.name == "New Name"
        assert updated.description == "Updated"
        assert updated.cidr == "10.0.1.0/24"  # unchanged

    # ── Delete ──────────────────────────────────────────────────

    def test_delete_subnet(self, db):
        """Deleting a subnet removes it from the database."""
        repo = SubnetRepository(db)
        subnet = repo.create(Subnet(name="ToDelete", cidr="10.0.1.0/24"))
        subnet_id = subnet.id

        repo.delete(subnet)

        assert repo.get_by_id(subnet_id) is None
        assert repo.count() == 0
