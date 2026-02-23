from __future__ import annotations

from typing import override

from django.db import IntegrityError

from app.domain.entities.user import User
from app.domain.exceptions import DuplicateUsernameError
from app.domain.repositories import UserRepository
from app.domain.value_objects import UserId, Username, UserPasswordHash, UserRole
from app.infrastructure.db.django_orm.models.user import UserModel


class UserRepositoryDjango(UserRepository):
    """Django ORM repository that maps Domain to Django model and back."""

    @staticmethod
    def _to_domain(orm: UserModel) -> User:
        """Rehydrate domain aggregate from Django ORM instance."""
        return User.from_storage(
            id=UserId(orm.id),
            username=Username(orm.username),
            password_hash=UserPasswordHash(bytes(orm.password_hash)),
            role=UserRole(orm.role),
            is_active=orm.is_active,
        )

    @override
    async def get_by_id(self, user_id: UserId) -> User | None:
        """Return a user by id or None."""
        try:
            orm = await UserModel.objects.aget(id=user_id.value)
        except UserModel.DoesNotExist:
            return None
        return self._to_domain(orm)

    @override
    async def get_by_username(self, username: Username) -> User | None:
        """Return a user by username or None."""
        try:
            orm = await UserModel.objects.aget(username=str(username))
        except UserModel.DoesNotExist:
            return None
        return self._to_domain(orm)

    @override
    async def add(self, user: User) -> None:
        """Persist a new user or raise on conflict."""
        try:
            await UserModel.objects.acreate(
                id=user.id.value,
                username=str(user.username),
                password_hash=user.password_hash.value,
                role=str(user.role),
                is_active=user.is_active,
            )
        except IntegrityError as e:
            raise DuplicateUsernameError(f"User {user.username} already exists") from e

    @override
    async def update(self, user: User) -> None:
        """Persist updated user state or raise on conflict."""
        try:
            updated = await UserModel.objects.filter(id=user.id.value).aupdate(
                username=str(user.username),
                password_hash=user.password_hash.value,
                role=str(user.role),
                is_active=user.is_active,
            )
        except IntegrityError as e:
            raise DuplicateUsernameError(
                f"Username {user.username} already exists"
            ) from e
        if not updated:
            raise ValueError(f"User {user.id} not found in database")

    @override
    async def get_all(self) -> list[User]:
        """Return all users from database."""
        return [self._to_domain(u) async for u in UserModel.objects.all()]
