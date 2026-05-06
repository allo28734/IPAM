"""
Subnet repository — Data Access Layer.

Extends BaseRepository with subnet-specific queries such as
CIDR lookup and overlap checking. Contains NO business logic.
"""

from typing import Sequence

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subnet import Subnet
from app.repositories.base import BaseRepository


class SubnetRepository(BaseRepository[Subnet]):
    """Data-access operations specific to the Subnet model."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Subnet, db)

    async def get_by_cidr(self, cidr: str) -> Subnet | None:
        """Find a subnet by its exact CIDR notation."""
        stmt = select(Subnet).where(Subnet.cidr == cidr)
        result = await self._db.scalars(stmt)
        return result.first()

    async def get_by_name(self, name: str) -> Subnet | None:
        """Find a subnet by its exact name."""
        stmt = select(Subnet).where(Subnet.name == name)
        result = await self._db.scalars(stmt)
        return result.first()

    async def search(self, query: str, *, skip: int = 0, limit: int = 100) -> Sequence[Subnet]:
        """
        Search subnets by partial match on name, CIDR, or description.

        This is a simple LIKE-based search suitable for the MVP.
        """
        pattern = f"%{query}%"
        stmt = (
            select(Subnet)
            .where(
                Subnet.name.ilike(pattern)
                | Subnet.cidr.ilike(pattern)
                | Subnet.description.ilike(pattern)
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self._db.scalars(stmt)
        return result.all()

    async def get_all_cidrs(self) -> list[str]:
        """
        Return all existing CIDR strings.

        Used by the service layer to perform overlap detection
        using Python's ipaddress module (business logic lives there,
        not here).
        """
        stmt = select(Subnet.cidr)
        result = await self._db.scalars(stmt)
        return list(result.all())

    async def find_overlapping(self, cidr: str) -> Sequence[Subnet]:
        """
        Return all existing subnets whose CIDR overlaps with the given CIDR.

        Delegates overlap detection entirely to PostgreSQL using
        native inet/cidr operators (&&), avoiding O(N) Python-side
        iteration per check.
        """
        stmt = text(
            "SELECT id FROM subnets WHERE cidr::inet <<= :cidr::inet "
            "OR cidr::inet >>= :cidr::inet"
        )
        result = await self._db.execute(stmt, {"cidr": cidr})
        overlapping_ids = [row[0] for row in result]
        if not overlapping_ids:
            return []
            
        stmt2 = select(Subnet).where(Subnet.id.in_(overlapping_ids))
        result2 = await self._db.scalars(stmt2)
        return list(result2.all())
