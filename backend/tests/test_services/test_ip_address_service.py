"""
Tests for IPAddressService — Business Logic Layer.

These tests verify that the service layer correctly enforces
IP allocation rules, membership validation, duplicate prevention,
status transitions, and auto-allocation.
"""

import pytest

from app.services.ip_address_service import (
    IPAddressService,
    IPConflictError,
    IPNotFoundError,
    IPValidationError,
    SubnetFullError,
    SubnetNotFoundError,
)
from app.services.subnet_service import SubnetService


@pytest.fixture(name="subnet")
def sample_subnet(db):
    """Create a subnet via the service for IP tests to use."""
    svc = SubnetService(db)
    return svc.create_subnet(name="Test Subnet", cidr="10.0.1.0/24", gateway="10.0.1.1")


class TestIPServiceAssign:
    """Tests for assigning specific IP addresses."""

    def test_assign_valid_ip(self, db, subnet):
        svc = IPAddressService(db)
        ip = svc.assign_ip(subnet.id, address="10.0.1.10", hostname="web-01")

        assert ip.id is not None
        assert ip.address == "10.0.1.10"
        assert ip.status == "assigned"
        assert ip.hostname == "web-01"

    def test_assign_reserved_status(self, db, subnet):
        svc = IPAddressService(db)
        ip = svc.assign_ip(subnet.id, address="10.0.1.20", status="reserved")

        assert ip.status == "reserved"

    def test_reject_invalid_ip_format(self, db, subnet):
        svc = IPAddressService(db)
        with pytest.raises(IPValidationError, match="Invalid IPv4"):
            svc.assign_ip(subnet.id, address="not-an-ip")

    def test_reject_ip_outside_subnet(self, db, subnet):
        svc = IPAddressService(db)
        with pytest.raises(IPValidationError, match="not within subnet"):
            svc.assign_ip(subnet.id, address="192.168.1.10")

    def test_reject_duplicate_ip(self, db, subnet):
        svc = IPAddressService(db)
        svc.assign_ip(subnet.id, address="10.0.1.10")

        with pytest.raises(IPConflictError, match="already tracked"):
            svc.assign_ip(subnet.id, address="10.0.1.10")

    def test_reject_invalid_status(self, db, subnet):
        svc = IPAddressService(db)
        with pytest.raises(IPValidationError, match="Invalid status"):
            svc.assign_ip(subnet.id, address="10.0.1.10", status="bogus")

    def test_reject_nonexistent_subnet(self, db):
        svc = IPAddressService(db)
        with pytest.raises(SubnetNotFoundError):
            svc.assign_ip(999, address="10.0.1.10")

    def test_assign_generates_audit_log(self, db, subnet):
        from app.models.audit_log import AuditLog
        from sqlalchemy import select

        svc = IPAddressService(db)
        svc.assign_ip(subnet.id, address="10.0.1.10")

        logs = db.scalars(
            select(AuditLog).where(AuditLog.entity_type == "ip_address")
        ).all()
        assert len(logs) >= 1


class TestIPServiceAutoAllocate:
    """Tests for auto-allocating the next available IP."""

    def test_allocate_first_available(self, db, subnet):
        """First available should be .2 (skipping .1 gateway)."""
        svc = IPAddressService(db)
        ip = svc.allocate_next_available(subnet.id)

        assert ip.address == "10.0.1.2"
        assert ip.status == "assigned"

    def test_allocate_skips_used(self, db, subnet):
        svc = IPAddressService(db)
        svc.assign_ip(subnet.id, address="10.0.1.2")

        ip = svc.allocate_next_available(subnet.id)
        assert ip.address == "10.0.1.3"

    def test_allocate_with_custom_status(self, db, subnet):
        svc = IPAddressService(db)
        ip = svc.allocate_next_available(subnet.id, status="reserved")

        assert ip.status == "reserved"

    def test_allocate_with_hostname(self, db, subnet):
        svc = IPAddressService(db)
        ip = svc.allocate_next_available(subnet.id, hostname="auto-host")

        assert ip.hostname == "auto-host"

    def test_allocate_nonexistent_subnet(self, db):
        svc = IPAddressService(db)
        with pytest.raises(SubnetNotFoundError):
            svc.allocate_next_available(999)

    def test_allocate_full_subnet(self, db):
        """A /30 has 2 usable hosts — allocating 3 should fail."""
        subnet_svc = SubnetService(db)
        small = subnet_svc.create_subnet(name="Tiny", cidr="10.0.99.0/30", gateway="10.0.99.1")

        svc = IPAddressService(db)
        svc.allocate_next_available(small.id)  # .2

        with pytest.raises(SubnetFullError, match="no available"):
            svc.allocate_next_available(small.id)


class TestIPServiceRead:
    """Tests for IP address retrieval."""

    def test_get_ip(self, db, subnet):
        svc = IPAddressService(db)
        created = svc.assign_ip(subnet.id, address="10.0.1.10")

        found = svc.get_ip(created.id)
        assert found.address == "10.0.1.10"

    def test_get_nonexistent_ip(self, db):
        svc = IPAddressService(db)
        with pytest.raises(IPNotFoundError):
            svc.get_ip(999)

    def test_list_ips_in_subnet(self, db, subnet):
        svc = IPAddressService(db)
        svc.assign_ip(subnet.id, address="10.0.1.10", status="assigned")
        svc.assign_ip(subnet.id, address="10.0.1.11", status="reserved")

        all_ips = svc.list_ips_in_subnet(subnet.id)
        assert len(all_ips) == 2

        assigned_only = svc.list_ips_in_subnet(subnet.id, status="assigned")
        assert len(assigned_only) == 1

    def test_list_ips_invalid_status(self, db, subnet):
        svc = IPAddressService(db)
        with pytest.raises(IPValidationError, match="Invalid status"):
            svc.list_ips_in_subnet(subnet.id, status="bogus")


class TestIPServiceUpdate:
    """Tests for IP address updates."""

    def test_update_hostname(self, db, subnet):
        svc = IPAddressService(db)
        ip = svc.assign_ip(subnet.id, address="10.0.1.10")

        updated = svc.update_ip(ip.id, hostname="new-host")
        assert updated.hostname == "new-host"

    def test_update_status(self, db, subnet):
        svc = IPAddressService(db)
        ip = svc.assign_ip(subnet.id, address="10.0.1.10")

        updated = svc.update_ip(ip.id, status="reserved")
        assert updated.status == "reserved"

    def test_update_invalid_status(self, db, subnet):
        svc = IPAddressService(db)
        ip = svc.assign_ip(subnet.id, address="10.0.1.10")

        with pytest.raises(IPValidationError, match="Invalid status"):
            svc.update_ip(ip.id, status="bogus")

    def test_update_nonexistent_ip(self, db):
        svc = IPAddressService(db)
        with pytest.raises(IPNotFoundError):
            svc.update_ip(999, hostname="ghost")


class TestIPServiceRelease:
    """Tests for releasing IP addresses."""

    def test_release_sets_available(self, db, subnet):
        svc = IPAddressService(db)
        ip = svc.assign_ip(subnet.id, address="10.0.1.10", hostname="web-01")

        released = svc.release_ip(ip.id)

        assert released.status == "available"
        assert released.hostname is None

    def test_release_nonexistent_ip(self, db):
        svc = IPAddressService(db)
        with pytest.raises(IPNotFoundError):
            svc.release_ip(999)

    def test_release_generates_audit_log(self, db, subnet):
        from app.models.audit_log import AuditLog
        from sqlalchemy import select

        svc = IPAddressService(db)
        ip = svc.assign_ip(subnet.id, address="10.0.1.10")
        svc.release_ip(ip.id)

        logs = db.scalars(
            select(AuditLog).where(AuditLog.action == "released")
        ).all()
        assert len(logs) == 1


class TestIPServiceDelete:
    """Tests for IP address hard deletion."""

    def test_delete_ip(self, db, subnet):
        svc = IPAddressService(db)
        ip = svc.assign_ip(subnet.id, address="10.0.1.10")

        svc.delete_ip(ip.id)

        with pytest.raises(IPNotFoundError):
            svc.get_ip(ip.id)

    def test_delete_nonexistent_ip(self, db):
        svc = IPAddressService(db)
        with pytest.raises(IPNotFoundError):
            svc.delete_ip(999)
