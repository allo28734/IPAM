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

import csv
import io
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
    is_subnet_of,
    subnets_overlap,
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
        parent_id: int | None = None,
        tags: dict | None = None,
        existing_subnets: list[Subnet] | None = None,
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
            network = validate_cidr(cidr)
            ip_version = network.version
        except ValueError as exc:
            raise SubnetValidationError(str(exc)) from exc

        # 1.5 SSRF Prevention Blocklist
        import ipaddress
        blocked_cidrs_v4 = [
            "0.0.0.0/8", "127.0.0.0/8", "169.254.169.254/32", "172.17.0.0/16",
        ]
        blocked_cidrs_v6 = ["::1/128", "fe80::/10", "fd00:ec2::254/128"]

        # Detect IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1/128)
        # and convert them to their real IPv4 representation before
        # blocklist evaluation, preventing trivial SSRF bypass.
        effective_network = network
        if network.version == 6 and network.network_address.ipv4_mapped:
            mapped_v4 = network.network_address.ipv4_mapped
            v4_prefix = network.prefixlen - 96  # IPv6→IPv4 prefix adjustment
            effective_network = ipaddress.ip_network(
                f"{mapped_v4}/{v4_prefix}", strict=False
            )
            ip_version = 4

        blocked_networks = [
            ipaddress.ip_network(b)
            for b in (blocked_cidrs_v4 if ip_version == 4 else blocked_cidrs_v6)
        ]

        for blocked in blocked_networks:
            if effective_network.overlaps(blocked):
                raise SubnetValidationError(
                    f"Creation of subnets overlapping with restricted infrastructure network ({blocked}) is prohibited for security reasons."
                )

        # 2. Parent validation and strict CIDR containment
        if parent_id is not None:
            parent = self.get_subnet(parent_id)
            if not is_subnet_of(cidr, parent.cidr):
                raise SubnetValidationError(
                    f"Child subnet {cidr} must be strictly contained within parent {parent.cidr}"
                )

        # 3. Check for overlaps with existing subnets
        #    Delegate to PostgreSQL for O(1)-per-check overlap detection
        #    when no cached list is provided.
        if existing_subnets is not None:
            overlapping = [
                s for s in existing_subnets if subnets_overlap(cidr, s.cidr)
            ]
        else:
            overlapping = self._repo.find_overlapping(cidr)

        for existing in overlapping:
            # Overlaps are ONLY allowed if the existing subnet is an ancestor
            is_ancestor = False
            curr_parent_id = parent_id
            while curr_parent_id is not None:
                if curr_parent_id == existing.id:
                    is_ancestor = True
                    break
                curr_parent = self.get_subnet(curr_parent_id)
                curr_parent_id = curr_parent.parent_id

            if not is_ancestor:
                raise SubnetConflictError(
                    f"Subnet {cidr} overlaps with existing subnet {existing.cidr} and is not a valid child."
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
            ip_version=ip_version,
            vlan_id=vlan_id,
            description=description,
            parent_id=parent_id,
            tags=tags or {},
        )
        created = self._repo.create(subnet)

        # Audit
        self._log_audit("subnet", created.id, "created", {
            "name": name, "cidr": cidr, "gateway": gateway, "parent_id": parent_id
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
        parent_id: int | None = None,
        tags: dict | None = None,
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
        if tags is not None:
            update_data["tags"] = tags
        
        # Parent validation
        if parent_id is not None:
            if parent_id == subnet_id:
                raise SubnetValidationError("A subnet cannot be its own parent")
            parent = self.get_subnet(parent_id)
            if not is_subnet_of(subnet.cidr, parent.cidr):
                raise SubnetValidationError(
                    f"Subnet {subnet.cidr} is not strictly contained within new parent {parent.cidr}"
                )
            # Cannot change parent if it causes new overlap conflicts with siblings
            # Wait, moving a subnet to a new parent doesn't change its CIDR, so overlaps won't change
            # UNLESS it was previously overlapping with the new parent's OTHER children!
            # But it couldn't have been, because we enforced overlaps on creation.
            # So just assigning parent_id is safe as long as containment is valid.
            update_data["parent_id"] = parent_id

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

    # ── Bulk Operations ──────────────────────────────────────────

    def export_csv(self) -> str:
        """Export all subnets to a CSV string."""
        subnets = self.list_subnets(limit=100000)
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "id", "name", "cidr", "gateway", "vlan_id", 
            "description", "parent_id", "tags"
        ])
        
        def sanitize(val):
            if isinstance(val, str) and val:
                stripped = val.lstrip()
                if stripped and stripped[0] in ('=', '+', '-', '@', '\t', '\r'):
                    return f"'{val}"
            return val
            
        for s in subnets:
            tags_str = json.dumps(s.tags) if s.tags else ""
            row = [
                s.id, s.name, s.cidr, s.gateway or "", s.vlan_id or "",
                s.description or "", s.parent_id or "", tags_str
            ]
            writer.writerow([sanitize(v) for v in row])
            
        return output.getvalue()

    # Maximum number of rows allowed per CSV import to prevent DoS
    MAX_IMPORT_ROWS = 1000

    def bulk_import(self, csv_file_obj) -> dict:
        """
        Import subnets from a CSV file iteratively.

        Security limits:
          - Maximum of MAX_IMPORT_ROWS rows per file.
          - Overlap detection is delegated to PostgreSQL per row
            (no O(N²) in-memory loop).

        Note: Parents must appear before children in the CSV file.
        """
        reader = csv.DictReader(csv_file_obj)

        created_count = 0
        errors = []

        for idx, row in enumerate(reader):
            # Enforce row limit to prevent CPU/memory exhaustion
            if idx >= self.MAX_IMPORT_ROWS:
                errors.append(
                    f"Import capped at {self.MAX_IMPORT_ROWS} rows. "
                    f"Remaining rows were skipped."
                )
                break

            name = row.get("name", "").strip()
            cidr = row.get("cidr", "").strip()
            if not name or not cidr:
                errors.append(f"Row {idx+1}: Missing required 'name' or 'cidr'")
                continue

            gateway = row.get("gateway", "").strip() or None
            vlan_id_str = row.get("vlan_id", "").strip()
            vlan_id = int(vlan_id_str) if vlan_id_str.isdigit() else None
            description = row.get("description", "").strip() or None
            parent_id_str = row.get("parent_id", "").strip()
            parent_id = int(parent_id_str) if parent_id_str.isdigit() else None

            tags_str = row.get("tags", "").strip()
            tags = {}
            if tags_str:
                try:
                    tags = json.loads(tags_str)
                except json.JSONDecodeError:
                    errors.append(f"Row {idx+1} ({cidr}): Invalid JSON in 'tags'")
                    continue

            try:
                # Overlap detection now delegated to PostgreSQL
                # (no existing_subnets cache passed)
                created = self.create_subnet(
                    name=name,
                    cidr=cidr,
                    gateway=gateway,
                    vlan_id=vlan_id,
                    description=description,
                    parent_id=parent_id,
                    tags=tags,
                )
                created_count += 1
            except (SubnetValidationError, SubnetConflictError) as e:
                errors.append(f"Row {idx+1} ({cidr}): {str(e)}")

        self._db.commit()
        return {"imported": created_count, "errors": errors}
