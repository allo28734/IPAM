"""
Pydantic schemas for IP Address API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Request schemas ─────────────────────────────────────────────


class IPAddressCreate(BaseModel):
    """Schema for assigning/reserving a specific IP address."""

    address: str = Field(..., min_length=7, max_length=15, examples=["10.0.1.10"])
    status: str = Field("assigned", examples=["assigned", "reserved"])
    hostname: Optional[str] = Field(None, max_length=255, examples=["web-server-01"])
    description: Optional[str] = Field(None, max_length=500, examples=["Production web server"])


class IPAddressAllocate(BaseModel):
    """Schema for auto-allocating the next available IP."""

    status: str = Field("assigned", examples=["assigned", "reserved"])
    hostname: Optional[str] = Field(None, max_length=255, examples=["app-server-02"])
    description: Optional[str] = Field(None, max_length=500)


class IPAddressUpdate(BaseModel):
    """Schema for updating IP address metadata. All fields optional."""

    status: Optional[str] = Field(None, examples=["assigned", "reserved", "available"])
    hostname: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)


# ── Response schemas ────────────────────────────────────────────


class IPAddressResponse(BaseModel):
    """Schema for IP address data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subnet_id: int
    address: str
    status: str
    hostname: Optional[str] = None
    description: Optional[str] = None
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class IPAddressListResponse(BaseModel):
    """List of IP addresses (within a subnet context)."""

    items: list[IPAddressResponse]
    total: int
