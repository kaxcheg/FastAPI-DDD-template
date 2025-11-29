from typing import override

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User
from app.domain.entities.user.repo import UserRepository
from app.domain.value_objects import UserId, Username, UserPasswordHash, UserRole

from app.application.exceptions import DuplicateUserError

from app.infrastructure.db.sqlalchemy.models.user import UserORM


class UserRepositorySQL(UserRepository):
    """SQLAlchemy repository that maps Domain to ORM and back."""

    def __init__(self, session: AsyncSession) -> None:
        """Store session bound to current UoW transaction."""
        self._s = session

    @override
    async def get_by_id(self, user_id: UserId) -> User | None:
        """Return a user by id or None."""
        result = await self._s.get(UserORM, user_id.value)
        if result is None:
            return None
        return User.from_storage(
            id=UserId(result.id),
            username=Username(result.username),
            password_hash=UserPasswordHash(result.password_hash),
            role=UserRole(result.role),
            is_active=result.is_active,
        )

    @override
    async def get_by_username(self, username: Username) -> User | None:
        """Return a user by username or None."""
        result = await self._s.scalars(
            select(UserORM).where(UserORM.username == str(username))
        )
        row = result.first()
        if row is None:
            return None
        return User.from_storage(
            id=UserId(row.id),
            username=Username(row.username),
            password_hash=UserPasswordHash(row.password_hash),
            role=UserRole(row.role),
            is_active=row.is_active,
        )

    @override
    async def add(self, user: User) -> None:
        """Persist a new user or raise on conflict."""
        user_orm = UserORM(
            id=user.id.value,
            username=str(user.username),
            password_hash=user.password_hash.value,
            role=str(user.role),
            is_active=user.is_active,
        )
        try:
            self._s.add(user_orm)
            await self._s.flush()
        except IntegrityError as e:
            raise DuplicateUserError(f"User {user.username} already exists") from e

    @override
    async def get_all(self) -> list[User]:
        """Return all users from database."""
        result = await self._s.scalars(select(UserORM))
        rows = result.all()
        return [
            User.from_storage(
                id=UserId(row.id),
                username=Username(row.username),
                password_hash=UserPasswordHash(row.password_hash),
                role=UserRole(row.role),
                is_active=row.is_active,
            )
            for row in rows
        ]
