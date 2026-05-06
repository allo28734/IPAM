"""
IP Address ORM model.

Represents a single IPv4 address within a subnet. Tracks allocation
status (available / assigned / reserved) and optional metadata like
hostname and description.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IPAddress(Base):
    """An individual IPv4 address belonging to a subnet."""

    __tablename__ = "ip_addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subnet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subnets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    address: Mapped[str] = mapped_column(String(45), nullable=False, unique=True)
    ip_version: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available"
    )
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    os_guess: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    source_integration_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("integration_providers.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="ID of the integration provider that last enriched this IP"
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

    # Relationship — each IP address belongs to one subnet
    subnet: Mapped["Subnet"] = relationship("Subnet", back_populates="ip_addresses")

    def __repr__(self) -> str:
        return f"<IPAddress(id={self.id}, address='{self.address}', status='{self.status}')>"
