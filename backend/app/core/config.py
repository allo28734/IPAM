"""
Application configuration via pydantic-settings.

Loads settings from environment variables and .env file.
All configuration is centralized here to keep the rest of the
application decoupled from environment specifics.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application metadata
    app_title: str = "IPAM — IP Address Management"
    app_version: str = "3.3.0"
    debug: bool = True

    # Database — PostgreSQL via Docker (see docker-compose.yml)
    database_url: str = "postgresql://ipam:ipam_secret@localhost:5432/ipam"

    # CORS — permissive for local development
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # JWT / Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # SSO / OIDC — optional, SSO is only active when all three are set
    sso_client_id: str | None = None
    sso_client_secret: str | None = None
    sso_discovery_url: str | None = None
    sso_admin_group: str | None = None

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Deep Discovery Encryption Key
    # Used for securely encrypting/decrypting SNMP profiles via Fernet.
    # In production, ALWAYS override this via .env using a securely generated key.
    # To generate a key, run: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str


# Singleton instance used across the application
settings = Settings()
