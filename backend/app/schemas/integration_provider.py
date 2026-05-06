"""
Pydantic schemas for Integration Provider API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Supported vendor types ──────────────────────────────────────

SUPPORTED_VENDORS = ["meraki", "fortigate", "aruba_central", "paloalto"]


# ── Request schemas ─────────────────────────────────────────────


class IntegrationProviderCreate(BaseModel):
    """Schema for creating a new integration provider."""

    name: str = Field(..., min_length=1, max_length=255, examples=["HQ Meraki Org"])
    vendor: str = Field(
        ..., min_length=1, max_length=50,
        examples=SUPPORTED_VENDORS,
        description="Vendor type. Must be one of: meraki, fortigate, aruba_central, paloalto"
    )
    is_enabled: bool = Field(True, description="Enable or disable this integration")
    base_url: Optional[str] = Field(
        None, max_length=500,
        examples=["https://192.168.1.1", "https://apigw-uswest4.central.arubanetworks.com"],
        description="API base URL (required for FortiGate, Aruba Central, Palo Alto)"
    )
    api_key: Optional[str] = Field(
        None, min_length=1,
        description="API key or token (encrypted at rest)"
    )
    username: Optional[str] = Field(
        None, max_length=255,
        description="Username (FortiGate admin auth or Aruba client_id)"
    )
    password: Optional[str] = Field(
        None, min_length=1,
        description="Password (FortiGate admin auth or Aruba client_secret; encrypted at rest)"
    )
    extra_config: Optional[dict] = Field(
        None,
        description="Vendor-specific settings (e.g., org_id for Meraki, vdom for FortiGate, "
                    "customer_id for Aruba, vsys for Palo Alto)",
        examples=[{"org_id": "123456"}]
    )
    auto_create_subnets: bool = Field(
        False,
        description="If true, auto-create discovered subnets. If false, hold for admin approval."
    )


class IntegrationProviderUpdate(BaseModel):
    """Schema for updating an integration provider. All fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_enabled: Optional[bool] = None
    base_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, min_length=1)
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=1)
    extra_config: Optional[dict] = None
    auto_create_subnets: Optional[bool] = None


# ── Response schemas ────────────────────────────────────────────


class IntegrationProviderResponse(BaseModel):
    """Schema for returning an integration provider (secrets omitted)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    vendor: str
    is_enabled: bool
    base_url: Optional[str] = None
    username: Optional[str] = None
    extra_config: Optional[dict] = None
    auto_create_subnets: bool
    last_sync_at: Optional[datetime] = None
    last_sync_status: str
    last_sync_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # NOTE: api_key_encrypted and password_encrypted are NEVER returned


class IntegrationProviderListResponse(BaseModel):
    """Paginated list of integration providers."""
    items: list[IntegrationProviderResponse]
    total: int


class ConnectionTestResponse(BaseModel):
    """Result of testing vendor API connectivity."""
    ok: bool
    message: str
    details: Optional[dict] = None


class SyncResultResponse(BaseModel):
    """Summary of a sync run."""
    provider_id: int
    provider_name: str
    status: str
    networks_found: int = 0
    clients_enriched: int = 0
    devices_found: int = 0
    subnets_created: int = 0
    subnets_suggested: int = 0
    errors: list[str] = []


class VendorInfo(BaseModel):
    """Metadata about a supported vendor."""
    id: str
    name: str
    description: str
    requires_base_url: bool
    supports_api_key: bool
    supports_username_password: bool
    extra_config_fields: list[dict]
