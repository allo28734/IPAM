"""
FastAPI dependency injection definitions.

Provides factory functions that create service instances with a
database session. These are used as FastAPI Depends() parameters
in the routers, keeping the routers thin and testable.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ip_address_service import IPAddressService
from app.services.subnet_service import SubnetService

# Type alias for a database session dependency
DbSession = Annotated[Session, Depends(get_db)]


def get_subnet_service(db: DbSession) -> SubnetService:
    """Create a SubnetService bound to the current request's DB session."""
    return SubnetService(db)


def get_ip_service(db: DbSession) -> IPAddressService:
    """Create an IPAddressService bound to the current request's DB session."""
    return IPAddressService(db)


# Type aliases for cleaner router signatures
SubnetServiceDep = Annotated[SubnetService, Depends(get_subnet_service)]
IPServiceDep = Annotated[IPAddressService, Depends(get_ip_service)]
