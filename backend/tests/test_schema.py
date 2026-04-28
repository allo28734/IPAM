"""
Tests for database schema creation and ORM model integrity.

Verifies that all tables are created correctly and that the
ORM models map to the expected columns and constraints.
"""

from sqlalchemy import inspect

from app.core.database import Base


class TestDatabaseSchema:
    """Verify the physical database schema matches our ORM definitions."""

    def test_all_tables_created(self, db):
        """All expected tables exist after create_all."""
        inspector = inspect(db.bind)
        table_names = inspector.get_table_names()

        assert "subnets" in table_names
        assert "ip_addresses" in table_names
        assert "audit_log" in table_names

    def test_subnets_columns(self, db):
        """The subnets table has all required columns."""
        inspector = inspect(db.bind)
        columns = {col["name"] for col in inspector.get_columns("subnets")}

        expected = {
            "id", "name", "cidr", "gateway", "vlan_id",
            "description", "created_at", "updated_at",
        }
        assert expected.issubset(columns)

    def test_ip_addresses_columns(self, db):
        """The ip_addresses table has all required columns."""
        inspector = inspect(db.bind)
        columns = {col["name"] for col in inspector.get_columns("ip_addresses")}

        expected = {
            "id", "subnet_id", "address", "status", "hostname",
            "description", "last_seen", "created_at", "updated_at",
        }
        assert expected.issubset(columns)

    def test_audit_log_columns(self, db):
        """The audit_log table has all required columns."""
        inspector = inspect(db.bind)
        columns = {col["name"] for col in inspector.get_columns("audit_log")}

        expected = {
            "id", "entity_type", "entity_id", "action",
            "details", "timestamp",
        }
        assert expected.issubset(columns)

    def test_ip_addresses_foreign_key(self, db):
        """ip_addresses.subnet_id references subnets.id."""
        inspector = inspect(db.bind)
        fkeys = inspector.get_foreign_keys("ip_addresses")

        subnet_fks = [
            fk for fk in fkeys
            if fk["referred_table"] == "subnets"
        ]
        assert len(subnet_fks) == 1
        assert "subnet_id" in subnet_fks[0]["constrained_columns"]

    def test_subnets_cidr_unique(self, db):
        """The cidr column on subnets has a unique constraint."""
        inspector = inspect(db.bind)
        unique_constraints = inspector.get_unique_constraints("subnets")
        indexes = inspector.get_indexes("subnets")

        # Check both unique constraints and unique indexes
        cidr_unique = any(
            "cidr" in uc.get("column_names", [])
            for uc in unique_constraints
        ) or any(
            idx.get("unique") and "cidr" in idx.get("column_names", [])
            for idx in indexes
        )
        assert cidr_unique, "cidr column should have a unique constraint"
