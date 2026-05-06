"""
System settings model.

Contains application-wide settings and feature toggles.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemSettings(Base):
    """
    Database model for system-wide configuration settings.
    Only one row is expected to exist in this table (id=1).
    """
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Application Domain (e.g., https://ipam.local)
    base_domain: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # SSO / OIDC Optional Settings
    sso_client_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sso_client_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    sso_discovery_url: Mapped[str | None] = mapped_column(String, nullable=True)
    sso_admin_group: Mapped[str | None] = mapped_column(String, nullable=True)

    # Feature Toggles
    enable_network_discovery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
