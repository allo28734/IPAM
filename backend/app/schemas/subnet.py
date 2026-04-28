"""
Pydantic schemas for Subnet API endpoints.

These schemas define the contract between the API layer and its
consumers. They handle serialization, deserialization, and
request validation at the HTTP boundary.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Request schemas ─────────────────────────────────────────────


class SubnetCreate(BaseModel):
    """Schema for creating a new subnet."""

    name: str = Field(..., min_length=1, max_length=255, examples=["Office LAN"])
    cidr: str = Field(..., min_length=7, max_length=18, examples=["10.0.1.0/24"])
    gateway: Optional[str] = Field(None, max_length=15, examples=["10.0.1.1"])
    vlan_id: Optional[int] = Field(None, ge=1, le=4094, examples=[100])
    description: Optional[str] = Field(None, max_length=500, examples=["Main office network"])


class SubnetUpdate(BaseModel):
    """Schema for updating subnet metadata. All fields are optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    gateway: Optional[str] = Field(None, max_length=15)
    vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    description: Optional[str] = Field(None, max_length=500)


# ── Response schemas ────────────────────────────────────────────


class SubnetResponse(BaseModel):
    """Schema for subnet data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cidr: str
    gateway: Optional[str] = None
    vlan_id: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SubnetUtilization(BaseModel):
    """Schema for subnet utilization statistics."""

    subnet_id: int
    cidr: str
    total_capacity: int
    used_count: int
    available_count: int
    utilization_percent: float
    first_usable_ip: str
    last_usable_ip: str


class SubnetListResponse(BaseModel):
    """Paginated list of subnets."""

    items: list[SubnetResponse]
    total: int


class DashboardStats(BaseModel):
    """Aggregate statistics for the dashboard."""

    total_subnets: int
    total_ips: int
    assigned_ips: int
    available_ips: int
    reserved_ips: int
    overall_utilization: float
