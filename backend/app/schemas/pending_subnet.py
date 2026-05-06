"""
Pydantic schemas for the Pending Subnet approval queue API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PendingSubnetResponse(BaseModel):
    """Schema for returning a pending subnet."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cidr: str
    name: Optional[str] = None
    gateway: Optional[str] = None
    vlan_id: Optional[int] = None
    ip_version: int
    description: Optional[str] = None
    status: str
    provider_id: int
    vendor: str
    raw_data: Optional[dict] = None
    discovered_at: datetime
    resolved_at: Optional[datetime] = None


class PendingSubnetListResponse(BaseModel):
    """Paginated list of pending subnets."""
    items: list[PendingSubnetResponse]
    total: int


class ApproveSubnetRequest(BaseModel):
    """Optional overrides when approving a pending subnet."""
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
