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
    base_domain: str | None = None
    sso_client_id: str | None = None
    sso_client_secret: str | None = None
    sso_discovery_url: str | None = None
    sso_admin_group: str | None = None


class SystemSettingsResponse(BaseModel):
    base_domain: str | None
    sso_client_id: str | None
    sso_discovery_url: str | None
    sso_admin_group: str | None
    # Omit sso_client_secret for security


@router.get("/settings", response_model=SystemSettingsResponse)
def get_settings(
    sys_settings: SystemSettingsDep,
    admin: CurrentAdmin,
):
    """Get current system settings (Admin only)."""
    return SystemSettingsResponse(
        base_domain=sys_settings.base_domain,
        sso_client_id=sys_settings.sso_client_id,
        sso_discovery_url=sys_settings.sso_discovery_url,
        sso_admin_group=sys_settings.sso_admin_group,
    )


@router.put("/settings", response_model=SystemSettingsResponse)
def update_settings(
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

    db.add(sys_settings)
    db.commit()
    db.refresh(sys_settings)

    return SystemSettingsResponse(
        base_domain=sys_settings.base_domain,
        sso_client_id=sys_settings.sso_client_id,
        sso_discovery_url=sys_settings.sso_discovery_url,
        sso_admin_group=sys_settings.sso_admin_group,
    )
