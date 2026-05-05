"""
Pydantic schemas for IP Address API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Request schemas ─────────────────────────────────────────────


class IPAddressCreate(BaseModel):
    """Schema for assigning/reserving a specific IP address."""

    address: str = Field(..., min_length=7, max_length=45, examples=["10.0.1.10", "2001:db8::1"])
    status: str = Field("assigned", examples=["assigned", "reserved"])
    hostname: Optional[str] = Field(None, max_length=255, examples=["web-server-01"])
    description: Optional[str] = Field(None, max_length=500, examples=["Production web server"])
    tags: Optional[dict[str, str]] = Field(None, description="Custom key-value metadata tags")


class IPAddressAllocate(BaseModel):
    """Schema for auto-allocating the next available IP."""

    status: str = Field("assigned", examples=["assigned", "reserved"])
    hostname: Optional[str] = Field(None, max_length=255, examples=["app-server-02"])
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[dict[str, str]] = Field(None)


class IPAddressUpdate(BaseModel):
    """Schema for updating IP address metadata. All fields optional."""

    status: Optional[str] = Field(None, examples=["assigned", "reserved", "available"])
    hostname: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    mac_address: Optional[str] = Field(None, max_length=17)
    vendor: Optional[str] = Field(None, max_length=255)
    os_guess: Optional[str] = Field(None, max_length=255)
    device_type: Optional[str] = Field(None, max_length=100)
    tags: Optional[dict[str, str]] = Field(None)


# ── Response schemas ────────────────────────────────────────────


class IPAddressResponse(BaseModel):
    """Schema for IP address data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subnet_id: int
    address: str
    ip_version: int
    status: str
    hostname: Optional[str] = None
    description: Optional[str] = None
    mac_address: Optional[str] = None
    vendor: Optional[str] = None
    os_guess: Optional[str] = None
    device_type: Optional[str] = None
    tags: Optional[dict[str, str]] = None
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class IPAddressListResponse(BaseModel):
    """List of IP addresses (within a subnet context)."""

    items: list[IPAddressResponse]
    total: int
