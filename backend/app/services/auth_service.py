"""
Authentication service — Business Logic Layer.

Handles password hashing, password verification, JWT token
generation, and user authentication.

SoC boundary: This module has NO knowledge of HTTP requests,
FastAPI Depends, or HTTPException. It receives plain Python
arguments and returns results or None.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.repositories.user_repo import UserRepository


# ── Password Utilities ─────────────────────────────────────────


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ── JWT Token ──────────────────────────────────────────────────


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Payload to encode (must include "sub" for the username).
        expires_delta: Optional custom expiry. Defaults to settings value.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


# ── Authentication ─────────────────────────────────────────────


def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> User | None:
    """
    Authenticate a user by username and password.

    Returns the User instance if credentials are valid, or None
    if the user is not found or the password is incorrect.
    """
    repo = UserRepository(db)
    user = repo.get_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
