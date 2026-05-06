"""
Adapter Registry — Factory for vendor adapters.

Maps vendor identifier strings to their concrete adapter classes.
To add a new vendor, create a new adapter module and register it here.
"""

from __future__ import annotations

from cryptography.fernet import Fernet

from app.integrations.base_adapter import BaseAdapter
from app.integrations.meraki_adapter import MerakiAdapter
from app.integrations.fortigate_adapter import FortiGateAdapter
from app.integrations.aruba_adapter import ArubaCentralAdapter
from app.integrations.paloalto_adapter import PaloAltoAdapter
from app.models.integration_provider import IntegrationProvider


ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "meraki": MerakiAdapter,
    "fortigate": FortiGateAdapter,
    "aruba_central": ArubaCentralAdapter,
    "paloalto": PaloAltoAdapter,
}


def get_adapter(provider: IntegrationProvider, fernet: Fernet) -> BaseAdapter:
    """
    Instantiate the correct adapter for a given IntegrationProvider.

    Raises ValueError if the vendor string is not recognized.
    """
    cls = ADAPTER_REGISTRY.get(provider.vendor)
    if cls is None:
        raise ValueError(
            f"Unknown vendor '{provider.vendor}'. "
            f"Supported: {', '.join(sorted(ADAPTER_REGISTRY))}"
        )
    return cls(provider, fernet)


def get_supported_vendors() -> list[dict]:
    """
    Return metadata for all supported vendors (used by the /vendors endpoint).
    """
    vendors = []
    for vendor_id, cls in ADAPTER_REGISTRY.items():
        vendors.append({
            "id": cls.VENDOR_ID,
            "name": cls.VENDOR_NAME,
            "description": cls.VENDOR_DESCRIPTION,
            "requires_base_url": cls.REQUIRES_BASE_URL,
            "supports_api_key": cls.SUPPORTS_API_KEY,
            "supports_username_password": cls.SUPPORTS_USERNAME_PASSWORD,
            "extra_config_fields": cls.EXTRA_CONFIG_FIELDS,
        })
    return vendors
