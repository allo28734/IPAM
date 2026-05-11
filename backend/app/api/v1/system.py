"""
System API router — Presentation Layer.

Endpoints for managing system-wide settings like SSO and Application Domain.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentAdmin, DbSession, SystemSettingsDep
from app.models.system_settings import SystemSettings

router = APIRouter(prefix="/system", tags=["system"])


class SystemSettingsUpdate(BaseModel):
    """Payload for updating application-wide system settings."""
    base_domain: str | None = None
    sso_client_id: str | None = None
    sso_client_secret: str | None = None
    sso_discovery_url: str | None = None
    sso_admin_group: str | None = None
    enable_network_discovery: bool | None = None


class SystemSettingsResponse(BaseModel):
    """Response model for system settings. Omits sensitive secrets."""
    base_domain: str | None
    sso_client_id: str | None
    sso_discovery_url: str | None
    sso_admin_group: str | None
    enable_network_discovery: bool
    # Omit sso_client_secret for security


@router.get("/settings", response_model=SystemSettingsResponse)
async def get_settings(
    sys_settings: SystemSettingsDep,
    admin: CurrentAdmin,
):
    """Get current system settings (Admin only)."""
    return SystemSettingsResponse(
        base_domain=sys_settings.base_domain,
        sso_client_id=sys_settings.sso_client_id,
        sso_discovery_url=sys_settings.sso_discovery_url,
        sso_admin_group=sys_settings.sso_admin_group,
        enable_network_discovery=sys_settings.enable_network_discovery,
    )


@router.put("/settings", response_model=SystemSettingsResponse)
async def update_settings(
    body: SystemSettingsUpdate,
    db: DbSession,
    sys_settings: SystemSettingsDep,
    admin: CurrentAdmin,
):
    """Update system settings (Admin only)."""
    if body.base_domain is not None:
        sys_settings.base_domain = body.base_domain
    if body.sso_client_id is not None:
        sys_settings.sso_client_id = body.sso_client_id
    if body.sso_client_secret is not None:
        sys_settings.sso_client_secret = body.sso_client_secret
    if body.sso_discovery_url is not None:
        sys_settings.sso_discovery_url = body.sso_discovery_url
    if body.sso_admin_group is not None:
        sys_settings.sso_admin_group = body.sso_admin_group
    if body.enable_network_discovery is not None:
        sys_settings.enable_network_discovery = body.enable_network_discovery

    db.add(sys_settings)
    await db.commit()
    await db.refresh(sys_settings)

    return SystemSettingsResponse(
        base_domain=sys_settings.base_domain,
        sso_client_id=sys_settings.sso_client_id,
        sso_discovery_url=sys_settings.sso_discovery_url,
        sso_admin_group=sys_settings.sso_admin_group,
        enable_network_discovery=sys_settings.enable_network_discovery,
    )


class FeatureFlagsResponse(BaseModel):
    enable_network_discovery: bool


@router.get("/features", response_model=FeatureFlagsResponse)
async def get_public_features(
    sys_settings: SystemSettingsDep,
):
    """Get public feature flags (No authentication required)."""
    return FeatureFlagsResponse(
        enable_network_discovery=sys_settings.enable_network_discovery,
    )


class DiscoveryHealthResponse(BaseModel):
    discovery_enabled: bool
    workers_online: bool


@router.get("/discovery-health", response_model=DiscoveryHealthResponse)
async def get_discovery_health(
    sys_settings: SystemSettingsDep,
):
    """
    Check if network discovery is enabled AND Celery workers are reachable.

    Returns both the feature flag state and whether at least one worker
    responded to a Celery ping. This lets the frontend warn the user
    when discovery is enabled in settings but no workers are running
    (e.g., Docker wasn't started with --profile discovery).
    """
    workers_online = False

    if sys_settings.enable_network_discovery:
        try:
            from app.core.celery_app import celery_app
            # ping() returns a list of dicts — one per worker that responded
            # Use a short timeout to avoid blocking the API request
            response = celery_app.control.ping(timeout=2.0)
            workers_online = len(response) > 0
        except Exception:
            workers_online = False

    return DiscoveryHealthResponse(
        discovery_enabled=sys_settings.enable_network_discovery,
        workers_online=workers_online,
    )

