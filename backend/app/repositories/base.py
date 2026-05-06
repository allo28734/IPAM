"""
Generic base repository providing reusable CRUD operations.

All entity-specific repositories inherit from this class. The base
repository is parameterized by the SQLAlchemy model type, enabling
type-safe operations without duplicating boilerplate across repos.

SoC boundary: This class handles ONLY database operations.
It must NOT contain business rules, validation logic, or HTTP concepts.
"""

from typing import Generic, TypeVar, Type, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

# Generic type variable bound to our declarative base
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository with standard CRUD operations.

    Usage:
        class SubnetRepo(BaseRepository[Subnet]):
            def __init__(self, db: AsyncSession):
                super().__init__(Subnet, db)
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession) -> None:
        self._model = model
        self._db = db

    # ── Read ────────────────────────────────────────────────────

    async def get_by_id(self, entity_id: int) -> ModelType | None:
        """Fetch a single record by primary key, or None if not found."""
        return await self._db.get(self._model, entity_id)

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelType]:
        """Fetch a paginated list of records."""
        stmt = select(self._model).offset(skip).limit(limit)
        result = await self._db.scalars(stmt)
        return result.all()

    async def count(self) -> int:
        """Return total number of records for this model."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self._model)
        result = await self._db.scalar(stmt)
        return result or 0

    # ── Create ──────────────────────────────────────────────────

    async def create(self, entity: ModelType) -> ModelType:
        """Add a new record to the database."""
        self._db.add(entity)
        await self._db.commit()
        await self._db.refresh(entity)
        return entity

    # ── Update ──────────────────────────────────────────────────

    async def update(self, entity: ModelType, update_data: dict) -> ModelType:
        """
        Apply a dictionary of changes to an existing record.

        Only keys present in update_data are modified; unmentioned
        columns remain unchanged.
        """
        for key, value in update_data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        await self._db.commit()
        await self._db.refresh(entity)
        return entity

    # ── Delete ──────────────────────────────────────────────────

    async def delete(self, entity: ModelType) -> None:
        """Remove a record from the database."""
        await self._db.delete(entity)
        await self._db.commit()
