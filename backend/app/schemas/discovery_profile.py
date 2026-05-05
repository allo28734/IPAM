"""
Pydantic schemas for Discovery Profile API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DiscoveryProfileCreate(BaseModel):
    """Schema for creating a new discovery profile."""

    name: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=255)
    auth_protocol: Optional[str] = Field(None, max_length=50, examples=["MD5", "SHA", "SHA224", "SHA256", "SHA384", "SHA512"])
    auth_password: Optional[str] = Field(None, min_length=1)
    priv_protocol: Optional[str] = Field(None, max_length=50, examples=["DES", "3DES", "AES", "AES192", "AES256"])
    priv_password: Optional[str] = Field(None, min_length=1)


class DiscoveryProfileUpdate(BaseModel):
    """Schema for updating a discovery profile."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    auth_protocol: Optional[str] = Field(None, max_length=50)
    auth_password: Optional[str] = Field(None, min_length=1)
    priv_protocol: Optional[str] = Field(None, max_length=50)
    priv_password: Optional[str] = Field(None, min_length=1)


class DiscoveryProfileResponse(BaseModel):
    """Schema for returning a discovery profile (passwords omitted)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str
    auth_protocol: Optional[str] = None
    priv_protocol: Optional[str] = None
    created_at: datetime
    updated_at: datetime
