"""
Tests for SubnetService — Business Logic Layer.

These tests verify that the service layer correctly enforces
domain rules (CIDR validation, overlap detection, gateway checks)
independently of the HTTP layer.
"""

import pytest

from app.services.subnet_service import (
    SubnetConflictError,
    SubnetNotFoundError,
    SubnetService,
    SubnetValidationError,
)


class TestSubnetServiceCreate:
    """Tests for subnet creation business rules."""

    def test_create_valid_subnet(self, db):
        """A valid subnet is persisted and returned with an ID."""
        svc = SubnetService(db)
        subnet = svc.create_subnet(name="Office", cidr="10.0.1.0/24", gateway="10.0.1.1")

        assert subnet.id is not None
        assert subnet.name == "Office"
        assert subnet.cidr == "10.0.1.0/24"
        assert subnet.gateway == "10.0.1.1"

    def test_create_subnet_without_gateway(self, db):
        """Gateway is optional."""
        svc = SubnetService(db)
        subnet = svc.create_subnet(name="NoGW", cidr="10.0.2.0/24")

        assert subnet.gateway is None

    def test_create_subnet_with_all_fields(self, db):
        """All optional fields can be set."""
        svc = SubnetService(db)
        subnet = svc.create_subnet(
            name="Full",
            cidr="10.0.3.0/24",
            gateway="10.0.3.1",
            vlan_id=100,
            description="Test subnet",
        )

        assert subnet.vlan_id == 100
        assert subnet.description == "Test subnet"

    def test_reject_invalid_cidr(self, db):
        """Invalid CIDR notation raises SubnetValidationError."""
        svc = SubnetService(db)
        with pytest.raises(SubnetValidationError, match="Invalid CIDR"):
            svc.create_subnet(name="Bad", cidr="not-a-cidr")

    def test_reject_cidr_with_host_bits(self, db):
        """CIDR with host bits set is rejected (strict mode)."""
        svc = SubnetService(db)
        with pytest.raises(SubnetValidationError, match="Invalid CIDR"):
            svc.create_subnet(name="Bad", cidr="10.0.1.5/24")

    def test_reject_overlapping_subnet(self, db):
        """Creating a subnet that overlaps an existing one raises SubnetConflictError."""
        svc = SubnetService(db)
        svc.create_subnet(name="Existing", cidr="10.0.1.0/24")

        with pytest.raises(SubnetConflictError, match="overlaps"):
            svc.create_subnet(name="Overlap", cidr="10.0.0.0/16")

    def test_reject_duplicate_cidr(self, db):
        """An identical CIDR is a special case of overlap."""
        svc = SubnetService(db)
        svc.create_subnet(name="First", cidr="10.0.1.0/24")

        with pytest.raises(SubnetConflictError, match="overlaps"):
            svc.create_subnet(name="Duplicate", cidr="10.0.1.0/24")

    def test_reject_gateway_outside_subnet(self, db):
        """Gateway must be within the CIDR range."""
        svc = SubnetService(db)
        with pytest.raises(SubnetValidationError, match="not within subnet"):
            svc.create_subnet(name="BadGW", cidr="10.0.1.0/24", gateway="192.168.1.1")

    def test_non_overlapping_subnets_allowed(self, db):
        """Non-overlapping subnets can coexist."""
        svc = SubnetService(db)
        svc.create_subnet(name="A", cidr="10.0.1.0/24")
        subnet_b = svc.create_subnet(name="B", cidr="10.0.2.0/24")

        assert subnet_b.id is not None

    def test_create_generates_audit_log(self, db):
        """Creating a subnet writes an audit log entry."""
        from app.models.audit_log import AuditLog
        from sqlalchemy import select

        svc = SubnetService(db)
        svc.create_subnet(name="Audited", cidr="10.0.1.0/24")

        logs = db.scalars(select(AuditLog)).all()
        assert len(logs) == 1
        assert logs[0].entity_type == "subnet"
        assert logs[0].action == "created"


class TestSubnetServiceRead:
    """Tests for subnet retrieval."""

    def test_get_existing_subnet(self, db):
        svc = SubnetService(db)
        created = svc.create_subnet(name="Test", cidr="10.0.1.0/24")

        found = svc.get_subnet(created.id)
        assert found.id == created.id

    def test_get_nonexistent_subnet(self, db):
        svc = SubnetService(db)
        with pytest.raises(SubnetNotFoundError):
            svc.get_subnet(999)

    def test_list_subnets(self, db):
        svc = SubnetService(db)
        svc.create_subnet(name="A", cidr="10.0.1.0/24")
        svc.create_subnet(name="B", cidr="10.0.2.0/24")

        subnets = svc.list_subnets()
        assert len(subnets) == 2

    def test_list_subnets_with_search(self, db):
        svc = SubnetService(db)
        svc.create_subnet(name="Office LAN", cidr="10.0.1.0/24")
        svc.create_subnet(name="Server Room", cidr="10.0.2.0/24")

        results = svc.list_subnets(search="office")
        assert len(results) == 1
        assert results[0].name == "Office LAN"


class TestSubnetServiceUtilization:
    """Tests for utilization computation."""

    def test_empty_subnet_utilization(self, db):
        svc = SubnetService(db)
        subnet = svc.create_subnet(name="Empty", cidr="10.0.1.0/24")

        util = svc.get_utilization(subnet.id)

        assert util["total_capacity"] == 254
        assert util["used_count"] == 0
        assert util["available_count"] == 254
        assert util["utilization_percent"] == 0.0
        assert util["first_usable_ip"] == "10.0.1.1"
        assert util["last_usable_ip"] == "10.0.1.254"

    def test_utilization_nonexistent_subnet(self, db):
        svc = SubnetService(db)
        with pytest.raises(SubnetNotFoundError):
            svc.get_utilization(999)


class TestSubnetServiceUpdate:
    """Tests for subnet updates."""

    def test_update_name(self, db):
        svc = SubnetService(db)
        subnet = svc.create_subnet(name="Old", cidr="10.0.1.0/24")

        updated = svc.update_subnet(subnet.id, name="New")
        assert updated.name == "New"

    def test_update_gateway_valid(self, db):
        svc = SubnetService(db)
        subnet = svc.create_subnet(name="Test", cidr="10.0.1.0/24")

        updated = svc.update_subnet(subnet.id, gateway="10.0.1.1")
        assert updated.gateway == "10.0.1.1"

    def test_update_gateway_invalid(self, db):
        svc = SubnetService(db)
        subnet = svc.create_subnet(name="Test", cidr="10.0.1.0/24")

        with pytest.raises(SubnetValidationError, match="not within subnet"):
            svc.update_subnet(subnet.id, gateway="192.168.1.1")

    def test_update_nonexistent_subnet(self, db):
        svc = SubnetService(db)
        with pytest.raises(SubnetNotFoundError):
            svc.update_subnet(999, name="Ghost")


class TestSubnetServiceDelete:
    """Tests for subnet deletion."""

    def test_delete_subnet(self, db):
        svc = SubnetService(db)
        subnet = svc.create_subnet(name="ToDelete", cidr="10.0.1.0/24")

        svc.delete_subnet(subnet.id)

        with pytest.raises(SubnetNotFoundError):
            svc.get_subnet(subnet.id)

    def test_delete_nonexistent_subnet(self, db):
        svc = SubnetService(db)
        with pytest.raises(SubnetNotFoundError):
            svc.delete_subnet(999)

    def test_delete_generates_audit_log(self, db):
        from app.models.audit_log import AuditLog
        from sqlalchemy import select

        svc = SubnetService(db)
        subnet = svc.create_subnet(name="Audited", cidr="10.0.1.0/24")
        svc.delete_subnet(subnet.id)

        logs = db.scalars(
            select(AuditLog).where(AuditLog.action == "deleted")
        ).all()
        assert len(logs) == 1
