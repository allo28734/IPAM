"""
Pydantic schemas for authentication and user management.

These schemas define the shape of request/response payloads
for the auth API endpoints. They contain NO business logic.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Token Schemas ──────────────────────────────────────────────


class Token(BaseModel):
    """Response payload for a successful authentication."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data extracted from a decoded JWT."""

    username: str | None = None


# ── User Schemas ───────────────────────────────────────────────


class UserCreate(BaseModel):
    """Payload for creating a new user."""

    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="readonly", pattern="^(admin|readonly)$")


class UserResponse(BaseModel):
    """Public user representation — never includes the password hash."""

    model_config = {"from_attributes": True}

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
