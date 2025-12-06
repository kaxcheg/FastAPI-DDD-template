from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from app.domain.entities.user import User
from app.domain.value_objects import UserPasswordHash, UserRawPassword


@runtime_checkable
class PasswordHasher(Protocol):
    """Hash raw password to secure hash."""

    def hash(self, raw_password: UserRawPassword, /) -> UserPasswordHash: ...


@runtime_checkable
class PasswordVerifier(Protocol):
    """Return True when raw password matches stored hash."""

    def verify(
        self, raw_password: UserRawPassword, hashed_password: UserPasswordHash
    ) -> bool: ...


class AuthService(ABC):
    """Authentication/authorization service contract."""

    @abstractmethod
    async def current_user(self) -> User: ...
