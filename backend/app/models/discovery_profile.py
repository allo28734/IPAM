"""
Discovery Profile ORM model.

Represents an SNMPv3 credentials profile used for deep discovery.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DiscoveryProfile(Base):
    """An SNMPv3 discovery profile."""

    __tablename__ = "discovery_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_protocol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    auth_password: Mapped[str | None] = mapped_column(String(500), nullable=True)
    priv_protocol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    priv_password: Mapped[str | None] = mapped_column(String(500), nullable=True)

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
        return f"<DiscoveryProfile(id={self.id}, name='{self.name}')>"
