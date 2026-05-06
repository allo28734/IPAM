"""
Integration Service — Business Logic Layer.

Orchestrates CRUD operations for IntegrationProviders, handles
credential encryption/decryption, and drives the sync engine that
reconciles vendor data with IPAM records.
"""

from __future__ import annotations

import ipaddress as ipmod
import logging
from datetime import datetime, timezone
from typing import List, Optional

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.base_adapter import BaseAdapter, NetworkData, ClientData
from app.integrations.registry import get_adapter, get_supported_vendors
from app.models.integration_provider import IntegrationProvider
from app.models.ip_address import IPAddress
from app.models.pending_subnet import PendingSubnet
from app.models.subnet import Subnet
from app.schemas.integration_provider import (
    IntegrationProviderCreate,
    IntegrationProviderUpdate,
    SUPPORTED_VENDORS,
)

logger = logging.getLogger(__name__)


class IntegrationServiceError(Exception):
    """Base exception for integration service errors."""


class IntegrationNotFoundError(IntegrationServiceError):
    """Raised when an integration provider is not found."""


class IntegrationService:
    """Business logic for managing vendor integrations and sync operations."""

    def __init__(self, db: AsyncSession):
        self._db = db
        self._fernet = Fernet(settings.encryption_key.encode())

    # ── Encryption helpers ─────────────────────────────────────

    def _encrypt(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        return self._fernet.encrypt(text.encode()).decode()

    def _decrypt(self, encrypted: Optional[str]) -> Optional[str]:
        if not encrypted:
            return None
        return self._fernet.decrypt(encrypted.encode()).decode()

    # ── CRUD ───────────────────────────────────────────────────

    async def create_provider(
        self, data: IntegrationProviderCreate
    ) -> IntegrationProvider:
        """Create a new integration provider with encrypted credentials."""
        if data.vendor not in SUPPORTED_VENDORS:
            raise IntegrationServiceError(
                f"Unsupported vendor '{data.vendor}'. "
                f"Supported: {', '.join(SUPPORTED_VENDORS)}"
            )

        # Check for duplicate name
        stmt = select(IntegrationProvider).where(
            IntegrationProvider.name == data.name
        )
        existing = (await self._db.scalars(stmt)).first()
        if existing:
            raise IntegrationServiceError(
                f"Integration with name '{data.name}' already exists."
            )

        provider = IntegrationProvider(
            name=data.name,
            vendor=data.vendor,
            is_enabled=data.is_enabled,
            base_url=data.base_url,
            api_key_encrypted=self._encrypt(data.api_key),
            username=data.username,
            password_encrypted=self._encrypt(data.password),
            extra_config=data.extra_config or {},
            auto_create_subnets=data.auto_create_subnets,
        )
        self._db.add(provider)
        await self._db.commit()
        await self._db.refresh(provider)
        return provider

    async def get_provider(self, provider_id: int) -> IntegrationProvider:
        provider = await self._db.get(IntegrationProvider, provider_id)
        if not provider:
            raise IntegrationNotFoundError(
                f"IntegrationProvider {provider_id} not found."
            )
        return provider

    async def list_providers(
        self, skip: int = 0, limit: int = 100
    ) -> List[IntegrationProvider]:
        stmt = (
            select(IntegrationProvider)
            .order_by(IntegrationProvider.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._db.scalars(stmt)
        return list(result.all())

    async def get_total_count(self) -> int:
        from sqlalchemy import func
        stmt = select(func.count(IntegrationProvider.id))
        result = await self._db.scalar(stmt)
        return result or 0

    async def update_provider(
        self, provider_id: int, data: IntegrationProviderUpdate
    ) -> IntegrationProvider:
        provider = await self.get_provider(provider_id)
        update_data = data.model_dump(exclude_unset=True)

        # Encrypt credential fields if provided
        if "api_key" in update_data:
            provider.api_key_encrypted = self._encrypt(update_data.pop("api_key"))
        if "password" in update_data:
            provider.password_encrypted = self._encrypt(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(provider, field, value)

        await self._db.commit()
        await self._db.refresh(provider)
        return provider

    async def delete_provider(self, provider_id: int) -> None:
        provider = await self.get_provider(provider_id)
        await self._db.delete(provider)
        await self._db.commit()

    # ── Connection test ────────────────────────────────────────

    async def test_connection(self, provider_id: int) -> dict:
        """Instantiate the adapter and test connectivity."""
        provider = await self.get_provider(provider_id)
        adapter = get_adapter(provider, self._fernet)
        return await adapter.test_connection()

    # ── Sync engine ────────────────────────────────────────────

    async def run_sync(self, provider_id: int) -> dict:
        """
        Execute a full sync cycle for a given integration provider.

        1. Fetch networks → create or suggest subnets
        2. Fetch clients → enrich existing IP records
        3. Fetch devices → enrich infrastructure IPs
        4. Update sync status
        """
        provider = await self.get_provider(provider_id)

        # Mark as in_progress
        provider.last_sync_status = "in_progress"
        provider.last_sync_error = None
        await self._db.commit()

        adapter = get_adapter(provider, self._fernet)
        result = {
            "provider_id": provider.id,
            "provider_name": provider.name,
            "status": "success",
            "networks_found": 0,
            "clients_enriched": 0,
            "devices_found": 0,
            "subnets_created": 0,
            "subnets_suggested": 0,
            "errors": [],
        }

        try:
            # ── Phase 1: Networks / Subnets ────────────────────
            networks = await adapter.fetch_networks()
            result["networks_found"] = len(networks)

            for net_data in networks:
                try:
                    await self._reconcile_network(provider, net_data, result)
                except Exception as e:
                    result["errors"].append(f"Network {net_data.cidr}: {e}")

            # ── Phase 2: Clients ───────────────────────────────
            clients = await adapter.fetch_clients()
            for client_data in clients:
                try:
                    enriched = await self._enrich_ip_from_client(
                        provider, client_data
                    )
                    if enriched:
                        result["clients_enriched"] += 1
                except Exception as e:
                    result["errors"].append(
                        f"Client {client_data.ip_address}: {e}"
                    )

            # ── Phase 3: Devices ───────────────────────────────
            devices = await adapter.fetch_devices()
            result["devices_found"] = len(devices)

            for dev_data in devices:
                if dev_data.ip_address:
                    try:
                        await self._enrich_ip_from_device(provider, dev_data)
                    except Exception as e:
                        result["errors"].append(
                            f"Device {dev_data.ip_address}: {e}"
                        )

            # ── Finalize ───────────────────────────────────────
            provider.last_sync_at = datetime.now(timezone.utc)
            provider.last_sync_status = "success"
            provider.last_sync_error = None

            if result["errors"]:
                result["status"] = "partial"
                provider.last_sync_error = "; ".join(result["errors"][:5])

            await self._db.commit()

        except Exception as e:
            logger.error(f"Sync failed for provider {provider.name}: {e}")
            provider.last_sync_status = "failed"
            provider.last_sync_error = str(e)[:1000]
            await self._db.commit()
            result["status"] = "failed"
            result["errors"].append(str(e))

        return result

    # ── Reconciliation helpers ─────────────────────────────────

    async def _reconcile_network(
        self,
        provider: IntegrationProvider,
        net_data: NetworkData,
        result: dict,
    ) -> None:
        """Match a vendor network to an existing subnet or create/suggest one."""
        # Normalize the CIDR
        try:
            network = ipmod.ip_network(net_data.cidr, strict=False)
            cidr = str(network)
        except ValueError:
            return

        # Check if subnet already exists
        stmt = select(Subnet).where(Subnet.cidr == cidr)
        existing = (await self._db.scalars(stmt)).first()

        if existing:
            # Update metadata if richer data is available
            if net_data.gateway and not existing.gateway:
                existing.gateway = net_data.gateway
            if net_data.vlan_id and not existing.vlan_id:
                existing.vlan_id = net_data.vlan_id
            return

        # Subnet is new — auto-create or queue for approval
        if provider.auto_create_subnets:
            new_subnet = Subnet(
                name=net_data.name or f"Auto: {cidr}",
                cidr=cidr,
                gateway=net_data.gateway,
                vlan_id=net_data.vlan_id,
                ip_version=4 if network.version == 4 else 6,
                description=net_data.description or f"Auto-created from {provider.name}",
            )
            self._db.add(new_subnet)
            result["subnets_created"] += 1
            logger.info(f"Auto-created subnet {cidr} from {provider.name}")
        else:
            # Check if already in the pending queue
            pending_stmt = select(PendingSubnet).where(
                PendingSubnet.cidr == cidr,
                PendingSubnet.status == "pending",
            )
            existing_pending = (await self._db.scalars(pending_stmt)).first()
            if not existing_pending:
                pending = PendingSubnet(
                    cidr=cidr,
                    name=net_data.name,
                    gateway=net_data.gateway,
                    vlan_id=net_data.vlan_id,
                    ip_version=4 if network.version == 4 else 6,
                    description=net_data.description,
                    provider_id=provider.id,
                    vendor=provider.vendor,
                    raw_data=net_data.raw if net_data.raw else None,
                )
                self._db.add(pending)
                result["subnets_suggested"] += 1
                logger.info(
                    f"Queued subnet {cidr} from {provider.name} for admin approval"
                )

    async def _enrich_ip_from_client(
        self,
        provider: IntegrationProvider,
        client: ClientData,
    ) -> bool:
        """
        Find an existing IPAddress record matching the client IP and
        enrich it with vendor data. Returns True if a record was updated.
        """
        stmt = select(IPAddress).where(IPAddress.address == client.ip_address)
        ip_record = (await self._db.scalars(stmt)).first()

        if not ip_record:
            return False

        # Update fields — only overwrite if the vendor provides richer data
        if client.mac_address and not ip_record.mac_address:
            ip_record.mac_address = client.mac_address
        if client.hostname and not ip_record.hostname:
            ip_record.hostname = client.hostname
        if client.vendor and not ip_record.vendor:
            ip_record.vendor = client.vendor
        if client.os and not ip_record.os_guess:
            ip_record.os_guess = client.os
        if client.device_type and not ip_record.device_type:
            ip_record.device_type = client.device_type

        # Always update last_seen and source
        ip_record.last_seen = datetime.now(timezone.utc)
        ip_record.source_integration_id = provider.id

        return True

    async def _enrich_ip_from_device(
        self,
        provider: IntegrationProvider,
        device,
    ) -> None:
        """Enrich an IP record from infrastructure device data."""
        if not device.ip_address:
            return

        stmt = select(IPAddress).where(IPAddress.address == device.ip_address)
        ip_record = (await self._db.scalars(stmt)).first()

        if not ip_record:
            return

        if device.name and not ip_record.hostname:
            ip_record.hostname = device.name
        if device.mac_address and not ip_record.mac_address:
            ip_record.mac_address = device.mac_address
        if device.device_type and not ip_record.device_type:
            ip_record.device_type = device.device_type

        ip_record.last_seen = datetime.now(timezone.utc)
        ip_record.source_integration_id = provider.id

    # ── Vendor metadata ────────────────────────────────────────

    @staticmethod
    def get_supported_vendors() -> list[dict]:
        return get_supported_vendors()
