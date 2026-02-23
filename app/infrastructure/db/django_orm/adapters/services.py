from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, override
from uuid import UUID

from app.application.exceptions import NotAuthenticatedError
from app.application.ports.services import AuthService
from app.application.ports.uow import UnitOfWork
from app.domain.entities.user import User
from app.domain.value_objects import UserId, Username, UserPasswordHash, UserRole
from app.infrastructure.db.django_orm.user_session_repo import UserSessionDjangoRepo


@dataclass
class AuthPayload:
    """JWT claims extracted by auth middleware."""

    user_id: UUID
    session_id: UUID
    role: str


class TokenSessionAuthServiceDjango(AuthService):
    """Auth facade using JWT payload and Django ORM session repository."""

    @override
    def __init__(
        self,
        payload: AuthPayload,
        uow_factory: Callable[[], UnitOfWork],
    ) -> None:
        """Store credentials and UoW factory."""
        self._uow_factory = uow_factory
        self._payload = payload

    @override
    async def current_user(self) -> User:
        """Return current user derived from payload or raise.

        :raises NotAuthenticatedError: If session is invalid or role mismatch.
        """
        async with self._uow_factory() as uow:
            session_repo = uow.get_repo(UserSessionDjangoRepo)
            user_orm = await session_repo.get_user_if_session_valid(
                self._payload.user_id, self._payload.session_id
            )
        if user_orm is None or user_orm.role != self._payload.role:
            raise NotAuthenticatedError("Not authorized.")

        return User.from_storage(
            id=UserId(user_orm.id),
            username=Username(user_orm.username),
            password_hash=UserPasswordHash(bytes(user_orm.password_hash)),
            role=UserRole(user_orm.role),
            is_active=user_orm.is_active,
        )
