"""
FastAPI dependency injection definitions.

Provides factory functions that create service instances with a
database session. These are used as FastAPI Depends() parameters
in the routers, keeping the routers thin and testable.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.ip_address_service import IPAddressService
from app.services.subnet_service import SubnetService

# Type alias for a database session dependency
DbSession = Annotated[AsyncSession, Depends(get_db)]

# OAuth2 scheme — points to the token endpoint for Swagger UI integration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# ── Service factories ──────────────────────────────────────────


def get_subnet_service(db: DbSession) -> SubnetService:
    """Create a SubnetService bound to the current request's DB session."""
    return SubnetService(db)


def get_ip_service(db: DbSession) -> IPAddressService:
    """Create an IPAddressService bound to the current request's DB session."""
    return IPAddressService(db)


# ── Auth dependencies ──────────────────────────────────────────


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    """
    Decode the JWT token and return the authenticated User.

    Raises HTTPException(401) if the token is missing, invalid,
    expired, or references a non-existent / inactive user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def get_current_active_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Ensure the current user has the 'admin' role.

    Raises HTTPException(403) if the user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


# ── Type aliases for cleaner router signatures ─────────────────
SubnetServiceDep = Annotated[SubnetService, Depends(get_subnet_service)]
IPServiceDep = Annotated[IPAddressService, Depends(get_ip_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_active_admin)]


from app.models.system_settings import SystemSettings

async def get_system_settings(db: DbSession) -> SystemSettings:
    """
    Dependency to fetch the single SystemSettings row from the database.
    Creates the row if it does not already exist.
    """
    stmt = select(SystemSettings).where(SystemSettings.id == 1)
    result = await db.scalars(stmt)
    settings = result.first()
    if not settings:
        settings = SystemSettings(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings

SystemSettingsDep = Annotated[SystemSettings, Depends(get_system_settings)]
