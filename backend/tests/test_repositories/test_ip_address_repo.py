"""
Tests for IPAddressRepository — Data Access Layer.

These tests verify that the repository correctly performs CRUD
operations and IP-specific queries. Allocation logic (which IP
to pick next) is a service concern, NOT tested here.
"""

import pytest

from app.models.ip_address import IPAddress
from app.models.subnet import Subnet
from app.repositories.ip_address_repo import IPAddressRepository
from app.repositories.subnet_repo import SubnetRepository


@pytest.fixture(name="subnet")
def sample_subnet(db):
    """Create a subnet fixture that IP addresses can belong to."""
    repo = SubnetRepository(db)
    return repo.create(Subnet(name="Test Subnet", cidr="10.0.1.0/24"))


class TestIPAddressRepository:
    """Test suite for IPAddressRepository CRUD and query operations."""

    # ── Create ──────────────────────────────────────────────────

    def test_create_ip(self, db, subnet):
        """Creating an IP address persists it with correct fields."""
        repo = IPAddressRepository(db)
        ip = IPAddress(
            subnet_id=subnet.id,
            address="10.0.1.10",
            status="assigned",
            hostname="web-server-01",
        )

        created = repo.create(ip)

        assert created.id is not None
        assert created.address == "10.0.1.10"
        assert created.status == "assigned"
        assert created.hostname == "web-server-01"
        assert created.subnet_id == subnet.id

    def test_create_ip_default_status(self, db, subnet):
        """IP addresses default to 'available' status."""
        repo = IPAddressRepository(db)
        ip = IPAddress(subnet_id=subnet.id, address="10.0.1.20")

        created = repo.create(ip)

        assert created.status == "available"

    # ── Read ────────────────────────────────────────────────────

    def test_get_by_id(self, db, subnet):
        """Retrieving an IP by ID returns the correct record."""
        repo = IPAddressRepository(db)
        ip = repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.30"))

        found = repo.get_by_id(ip.id)

        assert found is not None
        assert found.address == "10.0.1.30"

    def test_get_by_address(self, db, subnet):
        """Looking up by exact IP address string works."""
        repo = IPAddressRepository(db)
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.40"))

        found = repo.get_by_address("10.0.1.40")

        assert found is not None
        assert found.address == "10.0.1.40"

    def test_get_by_address_not_found(self, db, subnet):
        """Address lookup returns None for non-existent IPs."""
        repo = IPAddressRepository(db)

        assert repo.get_by_address("10.0.1.99") is None

    # ── Filter by subnet ────────────────────────────────────────

    def test_get_by_subnet(self, db, subnet):
        """Filtering by subnet returns only IPs in that subnet."""
        repo = IPAddressRepository(db)
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.10"))
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.11"))

        # Create a second subnet with its own IP
        subnet_repo = SubnetRepository(db)
        other = subnet_repo.create(Subnet(name="Other", cidr="192.168.1.0/24"))
        repo.create(IPAddress(subnet_id=other.id, address="192.168.1.10"))

        results = repo.get_by_subnet(subnet.id)

        assert len(results) == 2
        assert all(ip.subnet_id == subnet.id for ip in results)

    def test_get_by_subnet_with_status_filter(self, db, subnet):
        """Filtering by subnet + status narrows results correctly."""
        repo = IPAddressRepository(db)
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.10", status="assigned"))
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.11", status="available"))
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.12", status="reserved"))

        assigned = repo.get_by_subnet(subnet.id, status="assigned")
        assert len(assigned) == 1
        assert assigned[0].address == "10.0.1.10"

        available = repo.get_by_subnet(subnet.id, status="available")
        assert len(available) == 1

    # ── Counting ────────────────────────────────────────────────

    def test_count_by_subnet(self, db, subnet):
        """count_by_subnet returns correct totals."""
        repo = IPAddressRepository(db)

        assert repo.count_by_subnet(subnet.id) == 0

        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.10"))
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.11"))

        assert repo.count_by_subnet(subnet.id) == 2

    def test_count_by_subnet_and_status(self, db, subnet):
        """count_by_subnet_and_status filters correctly."""
        repo = IPAddressRepository(db)
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.10", status="assigned"))
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.11", status="assigned"))
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.12", status="available"))

        assert repo.count_by_subnet_and_status(subnet.id, "assigned") == 2
        assert repo.count_by_subnet_and_status(subnet.id, "available") == 1
        assert repo.count_by_subnet_and_status(subnet.id, "reserved") == 0

    def test_count_total_by_status(self, db, subnet):
        """count_total_by_status aggregates across all subnets."""
        repo = IPAddressRepository(db)
        subnet_repo = SubnetRepository(db)
        other = subnet_repo.create(Subnet(name="Other", cidr="192.168.1.0/24"))

        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.10", status="assigned"))
        repo.create(IPAddress(subnet_id=other.id, address="192.168.1.10", status="assigned"))
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.11", status="available"))

        assert repo.count_total_by_status("assigned") == 2
        assert repo.count_total_by_status("available") == 1

    # ── Get all addresses in subnet ─────────────────────────────

    def test_get_all_addresses_in_subnet(self, db, subnet):
        """get_all_addresses_in_subnet returns plain address strings."""
        repo = IPAddressRepository(db)
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.10"))
        repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.20"))

        addresses = repo.get_all_addresses_in_subnet(subnet.id)

        assert set(addresses) == {"10.0.1.10", "10.0.1.20"}

    # ── Update ──────────────────────────────────────────────────

    def test_update_ip(self, db, subnet):
        """Updating an IP modifies only specified fields."""
        repo = IPAddressRepository(db)
        ip = repo.create(
            IPAddress(subnet_id=subnet.id, address="10.0.1.10", status="available")
        )

        updated = repo.update(ip, {"status": "assigned", "hostname": "db-server-01"})

        assert updated.status == "assigned"
        assert updated.hostname == "db-server-01"
        assert updated.address == "10.0.1.10"  # unchanged

    # ── Delete ──────────────────────────────────────────────────

    def test_delete_ip(self, db, subnet):
        """Deleting an IP removes it from the database."""
        repo = IPAddressRepository(db)
        ip = repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.10"))
        ip_id = ip.id

        repo.delete(ip)

        assert repo.get_by_id(ip_id) is None

    # ── Cascade delete ──────────────────────────────────────────

    def test_cascade_delete_with_subnet(self, db, subnet):
        """Deleting a subnet cascades to its IP addresses."""
        ip_repo = IPAddressRepository(db)
        subnet_repo = SubnetRepository(db)

        ip_repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.10"))
        ip_repo.create(IPAddress(subnet_id=subnet.id, address="10.0.1.11"))

        assert ip_repo.count_by_subnet(subnet.id) == 2

        subnet_repo.delete(subnet)

        assert ip_repo.count_by_subnet(subnet.id) == 0
