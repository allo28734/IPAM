"""
Discovery Profile service — Business Logic Layer.

Orchestrates CRUD operations for DiscoveryProfiles and handles
the secure encryption/decryption of SNMP passwords.
"""

from typing import List, Optional
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.discovery_profile import DiscoveryProfile
from app.schemas.discovery_profile import DiscoveryProfileCreate, DiscoveryProfileUpdate

class DiscoveryProfileServiceError(Exception):
    """Base exception for discovery profile service errors."""
    pass

class DiscoveryProfileNotFoundError(DiscoveryProfileServiceError):
    """Raised when a discovery profile is not found."""
    pass

class DiscoveryProfileService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._fernet = Fernet(settings.encryption_key.encode())

    def _encrypt(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        return self._fernet.encrypt(text.encode()).decode()

    def _decrypt(self, encrypted_text: Optional[str]) -> Optional[str]:
        if not encrypted_text:
            return None
        return self._fernet.decrypt(encrypted_text.encode()).decode()

    async def create_profile(self, profile_in: DiscoveryProfileCreate) -> DiscoveryProfile:
        stmt = select(DiscoveryProfile).where(DiscoveryProfile.name == profile_in.name)
        result = await self._db.scalars(stmt)
        existing = result.first()
        if existing:
            raise DiscoveryProfileServiceError(f"Profile with name '{profile_in.name}' already exists.")

        profile = DiscoveryProfile(
            name=profile_in.name,
            username=profile_in.username,
            auth_protocol=profile_in.auth_protocol,
            auth_password=self._encrypt(profile_in.auth_password),
            priv_protocol=profile_in.priv_protocol,
            priv_password=self._encrypt(profile_in.priv_password)
        )
        self._db.add(profile)
        await self._db.commit()
        await self._db.refresh(profile)
        return profile

    async def get_profile(self, profile_id: int) -> DiscoveryProfile:
        profile = await self._db.get(DiscoveryProfile, profile_id)
        if not profile:
            raise DiscoveryProfileNotFoundError(f"DiscoveryProfile {profile_id} not found.")
        return profile

    async def get_decrypted_credentials(self, profile_id: int) -> dict:
        """Returns a dict with decrypted credentials for the worker."""
        profile = await self.get_profile(profile_id)
        return {
            "username": profile.username,
            "auth_protocol": profile.auth_protocol,
            "auth_password": self._decrypt(profile.auth_password),
            "priv_protocol": profile.priv_protocol,
            "priv_password": self._decrypt(profile.priv_password)
        }

    async def list_profiles(self, skip: int = 0, limit: int = 100) -> List[DiscoveryProfile]:
        stmt = select(DiscoveryProfile).offset(skip).limit(limit)
        result = await self._db.scalars(stmt)
        return list(result.all())

    async def update_profile(self, profile_id: int, profile_in: DiscoveryProfileUpdate) -> DiscoveryProfile:
        profile = await self.get_profile(profile_id)
        
        update_data = profile_in.model_dump(exclude_unset=True)
        
        if "auth_password" in update_data:
            update_data["auth_password"] = self._encrypt(update_data["auth_password"])
        if "priv_password" in update_data:
            update_data["priv_password"] = self._encrypt(update_data["priv_password"])
            
        for field, value in update_data.items():
            setattr(profile, field, value)
            
        await self._db.commit()
        await self._db.refresh(profile)
        return profile

    async def delete_profile(self, profile_id: int) -> None:
        profile = await self.get_profile(profile_id)
        await self._db.delete(profile)
        await self._db.commit()
