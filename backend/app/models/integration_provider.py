"""
Integration Provider ORM model.

Represents a vendor integration (e.g., Cisco Meraki, FortiGate, Aruba Central,
Palo Alto Networks) whose API is polled to enrich IPAM data.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IntegrationProvider(Base):
    """A configured vendor integration provider."""

    __tablename__ = "integration_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    vendor: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="One of: meraki, fortigate, aruba_central, paloalto"
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Connection details
    base_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="API endpoint URL (required for FortiGate, Aruba, Palo Alto; unused for Meraki)"
    )
    api_key_encrypted: Mapped[str | None] = mapped_column(
        String(1000), nullable=True,
        comment="Fernet-encrypted API key or token"
    )

    # Optional secondary credentials (e.g., FortiGate username/password auth)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_encrypted: Mapped[str | None] = mapped_column(
        String(1000), nullable=True,
        comment="Fernet-encrypted password (FortiGate admin auth fallback)"
    )

    # Vendor-specific configuration blob
    extra_config: Mapped[dict | None] = mapped_column(
        JSON, default=dict, nullable=True,
        comment="Vendor-specific settings: org_id, vdom, customer_id, vsys, etc."
    )

    # Sync behaviour
    auto_create_subnets: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="If True, auto-create subnets discovered by this integration. "
                "If False, hold them in an approval queue."
    )

    # Sync status tracking
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_sync_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="never",
        comment="One of: never, in_progress, success, failed"
    )
    last_sync_error: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<IntegrationProvider(id={self.id}, name='{self.name}', vendor='{self.vendor}')>"
