"""
User repository — Data Access Layer.

Extends BaseRepository with user-specific lookups such as
find-by-username and find-by-email. Contains NO business logic.
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data-access operations specific to the User model."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    async def get_by_username(self, username: str) -> User | None:
        """Find a user by their exact username."""
        stmt = select(User).where(User.username == username)
        result = await self._db.scalars(stmt)
        return result.first()

    async def get_by_email(self, email: str) -> User | None:
        """Find a user by their exact email address."""
        stmt = select(User).where(User.email == email)
        result = await self._db.scalars(stmt)
        return result.first()

    async def count_users(self) -> int:
        """Return the total number of users in the database."""
        stmt = select(func.count()).select_from(User)
        result = await self._db.scalar(stmt)
        return result or 0
