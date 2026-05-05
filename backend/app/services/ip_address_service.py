"""
IP Address service — Business Logic Layer.

Orchestrates IP address operations by combining repository data access
with domain validation rules. This layer enforces:
  - IP format validation
  - Membership validation (IP must belong to parent subnet)
  - Duplicate prevention (no two records for the same address)
  - Status transition rules
  - Auto-allocation of the next available address
  - Audit logging of all mutations

SoC boundary: This class has NO knowledge of HTTP requests/responses.
"""

import csv
import io
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.ip_address import IPAddress
from app.repositories.ip_address_repo import IPAddressRepository
from app.repositories.subnet_repo import SubnetRepository
from app.utils.ip_utils import (
    is_ip_in_subnet,
    next_available_ip,
    validate_ip_address,
)


class IPServiceError(Exception):
    """Base exception for IP address business-rule violations."""

    pass


class IPNotFoundError(IPServiceError):
    """Raised when a requested IP address does not exist."""

    pass


class IPConflictError(IPServiceError):
    """Raised when an IP operation violates a uniqueness constraint."""

    pass


class IPValidationError(IPServiceError):
    """Raised when input fails domain validation."""

    pass


class SubnetNotFoundError(IPServiceError):
    """Raised when the parent subnet does not exist."""

    pass


class SubnetFullError(IPServiceError):
    """Raised when a subnet has no available addresses."""

    pass


# Valid status values
VALID_STATUSES = {"available", "assigned", "reserved"}


class IPAddressService:
    """
    Business logic for IP address management.

    Receives a database session via constructor injection.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._ip_repo = IPAddressRepository(db)
        self._subnet_repo = SubnetRepository(db)

    # ── Queries ─────────────────────────────────────────────────

    def list_ips_in_subnet(
        self,
        subnet_id: int,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[IPAddress]:
        """List IP addresses in a subnet with optional status filter."""
        self._ensure_subnet_exists(subnet_id)

        if status and status not in VALID_STATUSES:
            raise IPValidationError(
                f"Invalid status '{status}'. Must be one of: "
                f"{', '.join(sorted(VALID_STATUSES))}"
            )

        return list(
            self._ip_repo.get_by_subnet(subnet_id, status=status, skip=skip, limit=limit)
        )

    def get_ip(self, ip_id: int) -> IPAddress:
        """Fetch a single IP address by ID or raise IPNotFoundError."""
        ip = self._ip_repo.get_by_id(ip_id)
        if not ip:
            raise IPNotFoundError(f"IP address with id {ip_id} not found")
        return ip

    def get_total_count(self) -> int:
        """Return the total number of IP address records."""
        return self._ip_repo.count()

    def get_total_count_by_status(self, status: str) -> int:
        """Return the total count of IPs with a given status."""
        return self._ip_repo.count_total_by_status(status)

    # ── Assign / Reserve a specific IP ──────────────────────────

    def assign_ip(
        self,
        subnet_id: int,
        *,
        address: str,
        status: str = "assigned",
        hostname: str | None = None,
        description: str | None = None,
        tags: dict | None = None,
    ) -> IPAddress:
        """
        Assign or reserve a specific IP address in a subnet.

        Validations:
          1. Parent subnet must exist
          2. Address must be valid IPv4
          3. Address must be within the parent subnet's CIDR
          4. Address must not already be tracked
          5. Status must be a valid value
        """
        subnet = self._ensure_subnet_exists(subnet_id)

        # Validate status
        if status not in VALID_STATUSES:
            raise IPValidationError(
                f"Invalid status '{status}'. Must be one of: "
                f"{', '.join(sorted(VALID_STATUSES))}"
            )

        # Validate IP format
        try:
            ip_obj = validate_ip_address(address)
            ip_version = ip_obj.version
        except ValueError as exc:
            raise IPValidationError(str(exc)) from exc

        # Enforce IP version matches subnet
        if ip_version != subnet.ip_version:
            raise IPValidationError(
                f"IP version mismatch: Subnet {subnet.cidr} is IPv{subnet.ip_version}, "
                f"but address {address} is IPv{ip_version}"
            )

        # Validate IP is within subnet
        if not is_ip_in_subnet(address, subnet.cidr):
            raise IPValidationError(
                f"Address {address} is not within subnet {subnet.cidr}"
            )

        # Check for duplicates
        existing = self._ip_repo.get_by_address(address)
        if existing:
            raise IPConflictError(
                f"Address {address} is already tracked "
                f"(status: {existing.status}, subnet_id: {existing.subnet_id})"
            )

        # Persist
        ip = IPAddress(
            subnet_id=subnet_id,
            address=address,
            ip_version=ip_version,
            status=status,
            hostname=hostname,
            description=description,
            tags=tags or {},
        )
        created = self._ip_repo.create(ip)

        self._log_audit("ip_address", created.id, status, {
            "address": address,
            "subnet_id": subnet_id,
            "hostname": hostname,
        })

        return created

    # ── Auto-allocate next available ────────────────────────────

    def allocate_next_available(
        self,
        subnet_id: int,
        *,
        status: str = "assigned",
        hostname: str | None = None,
        description: str | None = None,
        tags: dict | None = None,
    ) -> IPAddress:
        """
        Automatically allocate the next available IP in a subnet.

        Uses ip_utils.next_available_ip() to find the first free
        address, skipping the gateway and any already-tracked IPs.
        """
        subnet = self._ensure_subnet_exists(subnet_id)

        if status not in VALID_STATUSES:
            raise IPValidationError(
                f"Invalid status '{status}'. Must be one of: "
                f"{', '.join(sorted(VALID_STATUSES))}"
            )

        used = self._ip_repo.get_all_addresses_in_subnet(subnet_id)
        address = next_available_ip(subnet.cidr, used, gateway=subnet.gateway)

        if address is None:
            raise SubnetFullError(
                f"Subnet {subnet.cidr} has no available addresses"
            )

        ip = IPAddress(
            subnet_id=subnet_id,
            address=address,
            ip_version=subnet.ip_version,
            status=status,
            hostname=hostname,
            description=description,
            tags=tags or {},
        )
        created = self._ip_repo.create(ip)

        self._log_audit("ip_address", created.id, "auto_allocated", {
            "address": address,
            "subnet_id": subnet_id,
            "hostname": hostname,
        })

        return created

    # ── Update ──────────────────────────────────────────────────

    def update_ip(
        self,
        ip_id: int,
        *,
        status: str | None = None,
        hostname: str | None = None,
        description: str | None = None,
        mac_address: str | None = None,
        vendor: str | None = None,
        os_guess: str | None = None,
        device_type: str | None = None,
        tags: dict | None = None,
    ) -> IPAddress:
        """Update IP address metadata and/or status."""
        ip = self.get_ip(ip_id)

        if status is not None and status not in VALID_STATUSES:
            raise IPValidationError(
                f"Invalid status '{status}'. Must be one of: "
                f"{', '.join(sorted(VALID_STATUSES))}"
            )

        update_data = {}
        if status is not None:
            update_data["status"] = status
        if hostname is not None:
            update_data["hostname"] = hostname
        if description is not None:
            update_data["description"] = description
        if mac_address is not None:
            update_data["mac_address"] = mac_address
        if vendor is not None:
            update_data["vendor"] = vendor
        if os_guess is not None:
            update_data["os_guess"] = os_guess
        if device_type is not None:
            update_data["device_type"] = device_type
        if tags is not None:
            update_data["tags"] = tags

        if not update_data:
            return ip

        updated = self._ip_repo.update(ip, update_data)

        self._log_audit("ip_address", ip_id, "updated", update_data)

        return updated

    # ── Release (soft delete — set status to available) ─────────

    def release_ip(self, ip_id: int) -> IPAddress:
        """
        Release an IP address by setting its status to 'available'
        and clearing the hostname.
        """
        ip = self.get_ip(ip_id)
        old_status = ip.status

        updated = self._ip_repo.update(ip, {
            "status": "available",
            "hostname": None,
            "description": None,
        })

        self._log_audit("ip_address", ip_id, "released", {
            "address": ip.address,
            "previous_status": old_status,
        })

        return updated

    # ── Hard delete ─────────────────────────────────────────────

    def delete_ip(self, ip_id: int) -> None:
        """Permanently remove an IP address record."""
        ip = self.get_ip(ip_id)
        address = ip.address
        subnet_id = ip.subnet_id

        self._ip_repo.delete(ip)

        self._log_audit("ip_address", ip_id, "deleted", {
            "address": address,
            "subnet_id": subnet_id,
        })

    # ── Private helpers ─────────────────────────────────────────

    def _ensure_subnet_exists(self, subnet_id: int):
        """Fetch a subnet or raise SubnetNotFoundError."""
        subnet = self._subnet_repo.get_by_id(subnet_id)
        if not subnet:
            raise SubnetNotFoundError(
                f"Subnet with id {subnet_id} not found"
            )
        return subnet

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

    # ── Bulk Operations ──────────────────────────────────────────

    def export_csv(self, subnet_id: int) -> str:
        """Export all IPs in a subnet to a CSV string."""
        ips = self.list_ips_in_subnet(subnet_id, limit=100000)
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "id", "address", "status", "hostname", 
            "description", "tags"
        ])
        
        def sanitize(val):
            if isinstance(val, str) and val:
                stripped = val.lstrip()
                if stripped and stripped[0] in ('=', '+', '-', '@', '\t', '\r'):
                    return f"'{val}"
            return val
            
        for ip in ips:
            tags_str = json.dumps(ip.tags) if ip.tags else ""
            row = [
                ip.id, ip.address, ip.status, ip.hostname or "",
                ip.description or "", tags_str
            ]
            writer.writerow([sanitize(v) for v in row])
            
        return output.getvalue()

    def bulk_import(self, subnet_id: int, csv_file_obj) -> dict:
        """
        Import IP addresses from a CSV file into a specific subnet iteratively.
        """
        reader = csv.DictReader(csv_file_obj)
        
        created_count = 0
        errors = []
        
        for idx, row in enumerate(reader):
            address = row.get("address", "").strip()
            if not address:
                errors.append(f"Row {idx+1}: Missing required 'address'")
                continue
                
            status = row.get("status", "").strip() or "assigned"
            hostname = row.get("hostname", "").strip() or None
            description = row.get("description", "").strip() or None
            
            tags_str = row.get("tags", "").strip()
            tags = {}
            if tags_str:
                try:
                    tags = json.loads(tags_str)
                except json.JSONDecodeError:
                    errors.append(f"Row {idx+1} ({address}): Invalid JSON in 'tags'")
                    continue
                    
            try:
                self.assign_ip(
                    subnet_id=subnet_id,
                    address=address,
                    status=status,
                    hostname=hostname,
                    description=description,
                    tags=tags
                )
                created_count += 1
                if created_count % 1000 == 0:
                    self._db.commit()
            except (IPValidationError, IPConflictError, SubnetNotFoundError) as e:
                errors.append(f"Row {idx+1} ({address}): {str(e)}")
                
        self._db.commit()
        return {"imported": created_count, "errors": errors}
