from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, TypeVar, runtime_checkable

from app.application.dto import CredentialDTO
from app.domain.entities.user import User
from app.domain.entities.user.repo import UserRepository
from app.domain.value_objects import UserId, UserPasswordHash, UserRawPassword, UserRole


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


R = TypeVar("R", bound=UserRepository, contravariant=True)


class AuthService[R](ABC):
    """Authentication/authorization service contract."""

    _credentials: CredentialDTO

    def __init__(self, credentials: CredentialDTO) -> None:
        self._credentials = credentials

    @abstractmethod
    async def current_user(self, repo: R) -> User: ...

    @abstractmethod
    def ensure_role(
        self,
        user_id: UserId,
        user_role: UserRole,
        required_role: UserRole,
    ) -> None: ...
