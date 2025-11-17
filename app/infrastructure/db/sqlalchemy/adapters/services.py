import uuid
from dataclasses import dataclass
from typing import override
from uuid import UUID

from app.application.exceptions import NotAuthenticatedError, NotAuthorizedError
from app.application.ports.services import AuthService
from app.domain.entities.user import User
from app.domain.ports import IdGenerator
from app.domain.value_objects import UserId, Username, UserPasswordHash, UserRole
from app.infrastructure.db.sqlalchemy.user_session_service import UserSessionService


class UUIDv4Generator(IdGenerator):
    """Id generator that produces UUIDv4 values."""

    @override
    def new(self) -> UserId:
        """Return a new UserId."""
        return UserId(uuid.uuid4())


@dataclass
class AuthPayload:
    user_id: UUID
    session_id: UUID
    role: str


class TokenSessionAuthService(AuthService):
    """Auth facade using JWT and SQL repository."""

    @override
    def __init__(
        self,
        payload: AuthPayload,
        user_session_service: UserSessionService,
    ) -> None:
        """Store credentials and token service."""
        self._payload = payload
        self._user_session_service = user_session_service

    @override
    async def current_user(self) -> User:
        """Return current user derived from payload or raise."""

        user_orm = await self._user_session_service.get_user_if_session_valid(
            self._payload.user_id, self._payload.session_id
        )
        if user_orm is None or user_orm.role != self._payload.role:
            raise NotAuthenticatedError("Unauthorized")

        return User.from_storage(
            id=UserId(user_orm.id),
            username=Username(user_orm.username),
            password_hash=UserPasswordHash(user_orm.password_hash),
            role=UserRole(user_orm.role),
            is_active=user_orm.is_active,
        )

    @override
    def ensure_role(
        self, user_id: UserId, user_role: UserRole, required_role: UserRole
    ) -> None:
        """Raise when role is insufficient."""
        # Allow ADMIN and the exact target role.
        if user_role in {UserRole.ADMIN, required_role}:
            return
        raise NotAuthorizedError("Forbidden")
