"""
Integrations package.

Pluggable vendor adapter framework for pulling network data
from cloud-managed platforms into IPAM.
"""

from app.integrations.registry import get_adapter, ADAPTER_REGISTRY

__all__ = ["get_adapter", "ADAPTER_REGISTRY"]
