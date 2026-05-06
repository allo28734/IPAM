"""
IP Address repository — Data Access Layer.

Extends BaseRepository with IP-specific queries such as
filtering by subnet, status, and finding the next available address.
Contains NO business logic.
"""

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ip_address import IPAddress
from app.repositories.base import BaseRepository


class IPAddressRepository(BaseRepository[IPAddress]):
    """Data-access operations specific to the IPAddress model."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(IPAddress, db)

    async def get_by_address(self, address: str) -> IPAddress | None:
        """Find an IP by its exact address string."""
        stmt = select(IPAddress).where(IPAddress.address == address)
        result = await self._db.scalars(stmt)
        return result.first()

    async def get_by_subnet(
        self,
        subnet_id: int,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[IPAddress]:
        """
        List IP addresses belonging to a subnet.

        Optionally filter by status ('available', 'assigned', 'reserved').
        """
        stmt = select(IPAddress).where(IPAddress.subnet_id == subnet_id)
        if status:
            stmt = stmt.where(IPAddress.status == status)
        stmt = stmt.offset(skip).limit(limit)
        result = await self._db.scalars(stmt)
        return result.all()

    async def count_by_subnet(self, subnet_id: int) -> int:
        """Total number of IP records in a given subnet."""
        stmt = (
            select(func.count())
            .select_from(IPAddress)
            .where(IPAddress.subnet_id == subnet_id)
        )
        result = await self._db.scalar(stmt)
        return result or 0

    async def count_by_subnet_and_status(self, subnet_id: int, status: str) -> int:
        """Count IPs in a subnet with a specific status."""
        stmt = (
            select(func.count())
            .select_from(IPAddress)
            .where(
                IPAddress.subnet_id == subnet_id,
                IPAddress.status == status,
            )
        )
        result = await self._db.scalar(stmt)
        return result or 0

    async def get_all_addresses_in_subnet(self, subnet_id: int) -> list[str]:
        """
        Return all IP address strings in a subnet.

        Used by the service layer to compute the next available
        address — the allocation logic itself is in the service,
        not here.
        """
        stmt = select(IPAddress.address).where(IPAddress.subnet_id == subnet_id)
        result = await self._db.scalars(stmt)
        return list(result.all())

    async def count_total_by_status(self, status: str) -> int:
        """Count all IPs across all subnets with a given status."""
        stmt = (
            select(func.count())
            .select_from(IPAddress)
            .where(IPAddress.status == status)
        )
        result = await self._db.scalar(stmt)
        return result or 0
