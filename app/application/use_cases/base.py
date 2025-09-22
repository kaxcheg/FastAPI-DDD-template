from __future__ import annotations

from abc import ABC
from logging import Logger
from typing import Callable, final

from app.application.dto.base import DTO
from app.application.exceptions import NotAuthenticatedError, NotAuthorizedError
from app.application.ports import AuthPresenter, UnitOfWork
from app.application.ports.presenters import Presenter
from app.application.ports.services import AuthService
from app.config.logging import get_logger
from app.domain.entities.user.repo import UserRepository
from app.domain.exceptions.base import DomainError
from app.domain.value_objects import UserRole


class UseCase[I: DTO, O: DTO](ABC):
    """Application use case contract."""

    async def execute(self, dto: I, presenter: Presenter[O]) -> None: ...


class AuthorizeUserUseCase[I: DTO, O: DTO](ABC):
    """Use case base that checks authentication and role before execution."""

    _auth: AuthService[UserRepository]
    _required_role: UserRole
    _uow_factory: Callable[[], UnitOfWork]

    logger: Logger = get_logger(__name__)

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auth_service: AuthService[UserRepository],
        required_role: UserRole,
    ) -> None:
        """Initialize with UoW factory, auth service and target role."""
        self._uow_factory = uow_factory
        self._auth = auth_service
        self._required_role = required_role

    @final
    async def execute(self, dto: I, presenter: AuthPresenter[O]) -> None:
        """Run use case with authentication and role check."""
        try:
            async with self._uow_factory() as uow:
                user_repo = uow.get_repo(UserRepository)
                user = await self._auth.current_user(user_repo)
        except (NotAuthenticatedError, DomainError):
            presenter.unauthorized("Not authorized")
            return

        try:
            self._auth.ensure_role(user.id, user.role, self._required_role)
        except NotAuthorizedError:
            presenter.forbidden("Forbidden")
            self.logger.warning(
                {
                    "event": "access_denied",
                    "reason": "Insufficient role permissions",
                    "use_case": f"{self.__class__.__name__}",
                    "user_id": f"{user.id}",
                }
            )
            return

        await self.run(dto, presenter)

    async def run(self, dto: I, presenter: AuthPresenter[O]) -> None:
        """Execute domain logic after successful authorization."""
