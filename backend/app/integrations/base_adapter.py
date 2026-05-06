"""
Base Adapter — Abstract interface for all vendor integrations.

Every vendor adapter must subclass BaseAdapter and implement the
four abstract methods. The normalized dataclasses ensure that the
service layer never deals with vendor-specific data shapes.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from cryptography.fernet import Fernet

from app.models.integration_provider import IntegrationProvider

logger = logging.getLogger(__name__)


# ── Normalized data classes ────────────────────────────────────
# All adapters map vendor-specific responses into these structures
# so the service layer has a single, consistent interface.


@dataclass
class NetworkData:
    """A discovered subnet / VLAN from the vendor."""
    cidr: str                               # e.g. "10.0.1.0/24"
    name: str | None = None                 # human-readable label
    vlan_id: int | None = None
    gateway: str | None = None
    description: str | None = None
    ip_version: int = 4
    raw: dict = field(default_factory=dict)  # original vendor payload for debugging


@dataclass
class ClientData:
    """A client device observed on the network."""
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = None
    os: str | None = None
    vendor: str | None = None
    device_type: str | None = None
    vlan_id: int | None = None
    switch_port: str | None = None
    last_seen: str | None = None            # ISO-8601 string
    raw: dict = field(default_factory=dict)


@dataclass
class DeviceData:
    """A managed infrastructure device (switch, AP, firewall, etc.)."""
    ip_address: str | None = None
    mac_address: str | None = None
    name: str | None = None
    model: str | None = None
    serial: str | None = None
    firmware: str | None = None
    device_type: str | None = None
    raw: dict = field(default_factory=dict)


# ── Abstract Base Adapter ──────────────────────────────────────


class BaseAdapter(ABC):
    """
    Abstract base for all vendor integrations.

    Each adapter receives the IntegrationProvider ORM instance and a
    Fernet cipher used to decrypt stored credentials at call time.
    """

    # Human-readable vendor metadata (overridden by subclasses)
    VENDOR_ID: str = ""
    VENDOR_NAME: str = ""
    VENDOR_DESCRIPTION: str = ""
    REQUIRES_BASE_URL: bool = True
    SUPPORTS_API_KEY: bool = True
    SUPPORTS_USERNAME_PASSWORD: bool = False
    EXTRA_CONFIG_FIELDS: list[dict] = []

    def __init__(self, provider: IntegrationProvider, fernet: Fernet):
        self.provider = provider
        self._fernet = fernet

    # ── Credential helpers ─────────────────────────────────────

    def _decrypt(self, encrypted_text: Optional[str]) -> Optional[str]:
        """Decrypt a Fernet-encrypted string, returning None if empty."""
        if not encrypted_text:
            return None
        return self._fernet.decrypt(encrypted_text.encode()).decode()

    @property
    def api_key(self) -> Optional[str]:
        """Decrypted API key."""
        return self._decrypt(self.provider.api_key_encrypted)

    @property
    def password(self) -> Optional[str]:
        """Decrypted password."""
        return self._decrypt(self.provider.password_encrypted)

    @property
    def extra(self) -> dict:
        """Vendor-specific extra config dict (never None)."""
        return self.provider.extra_config or {}

    # ── Abstract interface ─────────────────────────────────────

    @abstractmethod
    async def test_connection(self) -> dict:
        """
        Validate that the stored credentials can reach the vendor API.

        Returns:
            {"ok": True/False, "message": "...", "details": {...}}
        """

    @abstractmethod
    async def fetch_networks(self) -> list[NetworkData]:
        """Retrieve subnets / VLANs from the vendor platform."""

    @abstractmethod
    async def fetch_clients(self) -> list[ClientData]:
        """Retrieve connected client devices."""

    @abstractmethod
    async def fetch_devices(self) -> list[DeviceData]:
        """Retrieve managed infrastructure devices."""
