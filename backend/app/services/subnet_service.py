"""
Subnet service — Business Logic Layer.

Orchestrates subnet operations by combining repository data access
with domain validation rules. This layer enforces:
  - CIDR format validation
  - Overlap detection (no two subnets may share IP space)
  - Gateway validation (must be within the subnet)
  - Utilization computation
  - Audit logging of all mutations

SoC boundary: This class has NO knowledge of HTTP requests/responses.
It receives plain Python arguments and returns model instances or
raises exceptions. The API layer catches these exceptions and maps
them to HTTP status codes.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.subnet import Subnet
from app.repositories.ip_address_repo import IPAddressRepository
from app.repositories.subnet_repo import SubnetRepository
from app.utils.ip_utils import (
    calculate_utilization,
    find_overlapping_cidrs,
    get_subnet_capacity,
    get_usable_host_range,
    is_ip_in_subnet,
    validate_cidr,
)


class SubnetServiceError(Exception):
    """Base exception for subnet business-rule violations."""

    pass


class SubnetNotFoundError(SubnetServiceError):
    """Raised when a requested subnet does not exist."""

    pass


class SubnetConflictError(SubnetServiceError):
    """Raised when a subnet operation violates a uniqueness constraint."""

    pass


class SubnetValidationError(SubnetServiceError):
    """Raised when input fails domain validation."""

    pass


class SubnetService:
    """
    Business logic for subnet management.

    Receives a database session via constructor injection.
    All public methods enforce domain rules before delegating to
    the repository for persistence.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = SubnetRepository(db)
        self._ip_repo = IPAddressRepository(db)

    # ── Queries ─────────────────────────────────────────────────

    def list_subnets(
        self, *, skip: int = 0, limit: int = 100, search: str | None = None
    ) -> list[Subnet]:
        """List subnets with optional search filtering."""
        if search:
            return list(self._repo.search(search, skip=skip, limit=limit))
        return list(self._repo.get_all(skip=skip, limit=limit))

    def get_subnet(self, subnet_id: int) -> Subnet:
        """Fetch a single subnet by ID or raise SubnetNotFoundError."""
        subnet = self._repo.get_by_id(subnet_id)
        if not subnet:
            raise SubnetNotFoundError(f"Subnet with id {subnet_id} not found")
        return subnet

    def get_utilization(self, subnet_id: int) -> dict:
        """
        Compute utilization statistics for a subnet.

        Returns a dict with total_capacity, used_count, available_count,
        utilization_percent, and host range info.
        """
        subnet = self.get_subnet(subnet_id)
        total = get_subnet_capacity(subnet.cidr)
        used = self._ip_repo.count_by_subnet(subnet_id)
        available = total - used
        pct = calculate_utilization(used, subnet.cidr)
        first_ip, last_ip, _ = get_usable_host_range(subnet.cidr)

        return {
            "subnet_id": subnet_id,
            "cidr": subnet.cidr,
            "total_capacity": total,
            "used_count": used,
            "available_count": available,
            "utilization_percent": pct,
            "first_usable_ip": first_ip,
            "last_usable_ip": last_ip,
        }

    def get_total_count(self) -> int:
        """Return the total number of subnets."""
        return self._repo.count()

    # ── Mutations ───────────────────────────────────────────────

    def create_subnet(
        self,
        *,
        name: str,
        cidr: str,
        gateway: str | None = None,
        vlan_id: int | None = None,
        description: str | None = None,
    ) -> Subnet:
        """
        Create a new subnet after validating all business rules.

        Validations:
          1. CIDR must be valid IPv4 notation
          2. CIDR must not overlap with any existing subnet
          3. Gateway (if provided) must be within the subnet
        """
        # 1. Validate CIDR format
        try:
            validate_cidr(cidr)
        except ValueError as exc:
            raise SubnetValidationError(str(exc)) from exc

        # 2. Check for overlaps with existing subnets
        existing_cidrs = self._repo.get_all_cidrs()
        overlaps = find_overlapping_cidrs(cidr, existing_cidrs)
        if overlaps:
            raise SubnetConflictError(
                f"Subnet {cidr} overlaps with existing subnet(s): "
                f"{', '.join(overlaps)}"
            )

        # 3. Validate gateway is within the subnet
        if gateway and not is_ip_in_subnet(gateway, cidr):
            raise SubnetValidationError(
                f"Gateway {gateway} is not within subnet {cidr}"
            )

        # Persist
        subnet = Subnet(
            name=name,
            cidr=cidr,
            gateway=gateway,
            vlan_id=vlan_id,
            description=description,
        )
        created = self._repo.create(subnet)

        # Audit
        self._log_audit("subnet", created.id, "created", {
            "name": name, "cidr": cidr, "gateway": gateway,
        })

        return created

    def update_subnet(
        self,
        subnet_id: int,
        *,
        name: str | None = None,
        gateway: str | None = None,
        vlan_id: int | None = None,
        description: str | None = None,
    ) -> Subnet:
        """
        Update subnet metadata.

        Note: CIDR cannot be changed after creation — that would
        invalidate all associated IP addresses.
        """
        subnet = self.get_subnet(subnet_id)

        # Validate new gateway if provided
        if gateway is not None and gateway and not is_ip_in_subnet(gateway, subnet.cidr):
            raise SubnetValidationError(
                f"Gateway {gateway} is not within subnet {subnet.cidr}"
            )

        update_data = {}
        if name is not None:
            update_data["name"] = name
        if gateway is not None:
            update_data["gateway"] = gateway
        if vlan_id is not None:
            update_data["vlan_id"] = vlan_id
        if description is not None:
            update_data["description"] = description

        if not update_data:
            return subnet

        updated = self._repo.update(subnet, update_data)

        self._log_audit("subnet", subnet_id, "updated", update_data)

        return updated

    def delete_subnet(self, subnet_id: int) -> None:
        """
        Delete a subnet and all its associated IP addresses (cascade).
        """
        subnet = self.get_subnet(subnet_id)
        cidr = subnet.cidr
        name = subnet.name

        self._repo.delete(subnet)

        self._log_audit("subnet", subnet_id, "deleted", {
            "name": name, "cidr": cidr,
        })

    # ── Audit helper ────────────────────────────────────────────

    def _log_audit(
        self, entity_type: str, entity_id: int, action: str, details: dict
    ) -> None:
        """Append an entry to the audit log."""
        log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=json.dumps(details),
            timestamp=datetime.now(timezone.utc),
        )
        self._db.add(log)
        self._db.commit()
