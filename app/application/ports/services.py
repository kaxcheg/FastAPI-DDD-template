from __future__ import annotations

from typing import Protocol, runtime_checkable, TypeVar

from app.domain.entities.user import User
from app.domain.entities.user.repo import UserRepository
from app.domain.value_objects import (
    UserId,
    UserPasswordHash,
    UserRawPassword,
    UserRole,
)

@runtime_checkable
class PasswordHasher(Protocol):
    """Hash raw password to secure hash."""

    def hash(self, raw_password: UserRawPassword, /) -> UserPasswordHash: ...


@runtime_checkable
class PasswordVerifier(Protocol):
    """Return True when raw password matches stored hash."""

    def verify(self, raw_password: UserRawPassword, hashed_password: UserPasswordHash) -> bool: ...

R = TypeVar("R", bound=UserRepository, covariant=True, contravariant=False)

class AuthService[R](Protocol):
    """Authentication/authorization service contract."""

    def ensure_role(self, user_id: UserId, role: UserRole, target_role: UserRole, ) -> None: ...
    async def current_user(self, repo: R) -> User: ...
