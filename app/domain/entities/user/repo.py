from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.base import Repository
from app.domain.entities.user import User
from app.domain.value_objects import UserId, Username


class UserRepository(ABC, Repository):
    """Repository contract for user entities."""

    @abstractmethod
    async def get_by_username(self, username: Username) -> User | None:
        """Return user by username.

        Args:
            username: Unique username.

        Returns:
            User | None: Found user or None.
        """
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None:
        """Return user by identifier.

        Args:
            user_id: Unique identifier.

        Returns:
            User | None: Found user or None.
        """
        ...

    @abstractmethod
    async def add(self, user: User) -> None:
        """Persist user.

        Args:
            user: User domain entity.
        """
        ...

    @abstractmethod
    async def update(self, user: User) -> None:
        """Persist changes to an existing user.

        Args:
            user: User domain entity with updated state.
        """
        ...

    @abstractmethod
    async def get_all(self) -> list[User]:
        """Return all users.

        Returns:
            list[User]: List of all user entities.
        """
        ...
