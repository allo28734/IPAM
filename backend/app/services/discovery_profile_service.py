"""
Discovery Profile service — Business Logic Layer.

Orchestrates CRUD operations for DiscoveryProfiles and handles
the secure encryption/decryption of SNMP passwords.
"""

from typing import List, Optional
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.discovery_profile import DiscoveryProfile
from app.schemas.discovery_profile import DiscoveryProfileCreate, DiscoveryProfileUpdate

class DiscoveryProfileServiceError(Exception):
    pass

class DiscoveryProfileNotFoundError(DiscoveryProfileServiceError):
    pass

class DiscoveryProfileService:
    def __init__(self, db: Session):
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

    def create_profile(self, profile_in: DiscoveryProfileCreate) -> DiscoveryProfile:
        existing = self._db.query(DiscoveryProfile).filter(DiscoveryProfile.name == profile_in.name).first()
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
        self._db.commit()
        self._db.refresh(profile)
        return profile

    def get_profile(self, profile_id: int) -> DiscoveryProfile:
        profile = self._db.query(DiscoveryProfile).filter(DiscoveryProfile.id == profile_id).first()
        if not profile:
            raise DiscoveryProfileNotFoundError(f"DiscoveryProfile {profile_id} not found.")
        return profile

    def get_decrypted_credentials(self, profile_id: int) -> dict:
        """Returns a dict with decrypted credentials for the worker."""
        profile = self.get_profile(profile_id)
        return {
            "username": profile.username,
            "auth_protocol": profile.auth_protocol,
            "auth_password": self._decrypt(profile.auth_password),
            "priv_protocol": profile.priv_protocol,
            "priv_password": self._decrypt(profile.priv_password)
        }

    def list_profiles(self, skip: int = 0, limit: int = 100) -> List[DiscoveryProfile]:
        return self._db.query(DiscoveryProfile).offset(skip).limit(limit).all()

    def update_profile(self, profile_id: int, profile_in: DiscoveryProfileUpdate) -> DiscoveryProfile:
        profile = self.get_profile(profile_id)
        
        update_data = profile_in.model_dump(exclude_unset=True)
        
        if "auth_password" in update_data:
            update_data["auth_password"] = self._encrypt(update_data["auth_password"])
        if "priv_password" in update_data:
            update_data["priv_password"] = self._encrypt(update_data["priv_password"])
            
        for field, value in update_data.items():
            setattr(profile, field, value)
            
        self._db.commit()
        self._db.refresh(profile)
        return profile

    def delete_profile(self, profile_id: int) -> None:
        profile = self.get_profile(profile_id)
        self._db.delete(profile)
        self._db.commit()
