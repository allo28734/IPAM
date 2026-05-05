from sqlalchemy import Column, Integer, String
from app.core.database import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"

    # We only ever want one row, so we can just use id=1
    id = Column(Integer, primary_key=True, index=True)
    
    # Application Domain (e.g., https://ipam.local)
    base_domain = Column(String, nullable=True)
    
    # SSO / OIDC Optional Settings
    sso_client_id = Column(String, nullable=True)
    sso_client_secret = Column(String, nullable=True)
    sso_discovery_url = Column(String, nullable=True)
    sso_admin_group = Column(String, nullable=True)

    # Feature Toggles
    enable_network_discovery = Column(Boolean, nullable=False, default=True)
