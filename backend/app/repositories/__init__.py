"""
Repository classes — Data Access Layer.

Repositories handle all direct database interactions (CRUD).
They contain NO business logic and NO HTTP awareness.
"""

from app.repositories.base import BaseRepository
from app.repositories.ip_address_repo import IPAddressRepository
from app.repositories.subnet_repo import SubnetRepository
from app.repositories.user_repo import UserRepository

__all__ = ["BaseRepository", "SubnetRepository", "IPAddressRepository", "UserRepository"]
