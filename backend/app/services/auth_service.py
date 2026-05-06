"""
Authentication service — Business Logic Layer.

Handles password hashing, password verification, JWT token
generation, user authentication, and SSO user provisioning.

SoC boundary: This module has NO knowledge of HTTP requests,
FastAPI Depends, or HTTPException. It receives plain Python
arguments and returns results or None.
"""

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.models.system_settings import SystemSettings
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


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User | None:
    """
    Authenticate a user by username and password.

    Returns the User instance if credentials are valid, or None
    if the user is not found or the password is incorrect.
    """
    repo = UserRepository(db)
    user = await repo.get_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def is_setup_required(db: AsyncSession) -> bool:
    """Check if the system requires first-run setup (0 users)."""
    repo = UserRepository(db)
    count = await repo.count_users()
    return count == 0


# ── SSO / OIDC ─────────────────────────────────────────────────


async def handle_sso_login(
    db: AsyncSession,
    email: str,
    username: str,
    user_groups: list[str],
    sys_settings: SystemSettings,
) -> User:
    """
    Provision or update a user from an SSO/OIDC login.

    Role evaluation:
        If sys_settings.sso_admin_group is set and appears in
        user_groups, the target role is "admin".
        Otherwise, the target role is "readonly".

    Auto-provision:
        If no user with the given email exists, a new User is
        created with a random impossible password.

    Role sync:
        If the user already exists, their role is updated to
        match the target role derived from the IdP groups.

    Returns:
        The provisioned or updated User instance.
    """
    # Determine target role from IdP groups
    target_role = "readonly"
    if sys_settings.sso_admin_group and sys_settings.sso_admin_group in user_groups:
        target_role = "admin"

    repo = UserRepository(db)
    user = await repo.get_by_email(email)

    if user is None:
        # Prevent username collision
        base_username = username
        while await repo.get_by_username(username) is not None:
            username = f"{base_username}_{secrets.token_hex(4)}"

        # Auto-provision with an impossible random password
        impossible_password = secrets.token_hex(32)
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(impossible_password),
            role=target_role,
        )
        user = await repo.create(user)
    else:
        # Sync role from IdP on every login
        if user.role != target_role:
            user.role = target_role
            await db.commit()
            await db.refresh(user)

    return user

