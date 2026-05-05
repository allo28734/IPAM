import pytest
from app.models.discovery_profile import DiscoveryProfile
from app.schemas.discovery_profile import DiscoveryProfileCreate, DiscoveryProfileUpdate
from app.services.discovery_profile_service import DiscoveryProfileService

def test_encryption_and_decryption(db):
    service = DiscoveryProfileService(db)
    
    profile_in = DiscoveryProfileCreate(
        name="Test SNMPv3",
        username="admin",
        auth_protocol="SHA",
        auth_password="supersecret_auth",
        priv_protocol="AES",
        priv_password="supersecret_priv"
    )
    
    # Create the profile
    profile = service.create_profile(profile_in)
    
    # 1. Verify it was encrypted in the DB
    assert profile.auth_password != "supersecret_auth"
    assert profile.priv_password != "supersecret_priv"
    # Ensure it's stored as an encrypted string (Fernet produces bytes, we decode to string)
    assert type(profile.auth_password) == str
    assert type(profile.priv_password) == str
    
    # 2. Verify we can decrypt it correctly via the service
    creds = service.get_decrypted_credentials(profile.id)
    assert creds["username"] == "admin"
    assert creds["auth_password"] == "supersecret_auth"
    assert creds["priv_password"] == "supersecret_priv"

def test_update_encryption(db):
    service = DiscoveryProfileService(db)
    profile_in = DiscoveryProfileCreate(
        name="Update Test",
        username="admin",
        auth_password="old_password"
    )
    profile = service.create_profile(profile_in)
    
    original_encrypted_password = profile.auth_password
    
    # Update password
    update_in = DiscoveryProfileUpdate(auth_password="new_password")
    updated = service.update_profile(profile.id, update_in)
    
    # Verify encrypted in DB and it changed
    assert updated.auth_password != "new_password"
    assert updated.auth_password != original_encrypted_password
    
    # Verify decrypt
    creds = service.get_decrypted_credentials(profile.id)
    assert creds["auth_password"] == "new_password"
