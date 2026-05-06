"""
Pending Subnet ORM model.

Represents a subnet discovered by a vendor integration that has not
yet been approved by an administrator. When an IntegrationProvider has
auto_create_subnets=False, discovered networks land here instead of
being created directly in the subnets table.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PendingSubnet(Base):
    """A vendor-discovered subnet awaiting admin approval."""

    __tablename__ = "pending_subnets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Network data (same shape as the Subnet model)
    cidr: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gateway: Mapped[str | None] = mapped_column(String(45), nullable=True)
    vlan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip_version: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Approval workflow
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="One of: pending, approved, dismissed"
    )

    # Source tracking
    provider_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("integration_providers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    vendor: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Denormalized vendor name for display convenience"
    )

    # Metadata stored from the adapter (e.g., DHCP scope info, raw data)
    raw_data: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)

    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp when the admin approved or dismissed this entry"
    )

    # Relationship to the integration provider
    provider: Mapped["IntegrationProvider"] = relationship(
        "IntegrationProvider", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<PendingSubnet(id={self.id}, cidr='{self.cidr}', status='{self.status}')>"
