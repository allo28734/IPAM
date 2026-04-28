"""
Subnet ORM model.

Represents a network subnet (e.g. 10.0.1.0/24). Each subnet can
contain many IP addresses via the one-to-many relationship.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Subnet(Base):
    """A network subnet defined by a CIDR block."""

    __tablename__ = "subnets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cidr: Mapped[str] = mapped_column(String(18), nullable=False, unique=True)
    gateway: Mapped[str | None] = mapped_column(String(15), nullable=True)
    vlan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

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

    # Relationship — one subnet has many IP addresses
    ip_addresses: Mapped[list["IPAddress"]] = relationship(
        "IPAddress",
        back_populates="subnet",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Subnet(id={self.id}, name='{self.name}', cidr='{self.cidr}')>"
