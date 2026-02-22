from __future__ import annotations

from typing import Callable, override

from app.application.dto import GetUserInputDTO, GetUserOutputDTO, UserDTO
from app.application.ports.presenters import AuthPresenter
from app.application.ports.services import AuthService
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.base import AuthorizeUserUseCase
from app.config.logging import get_logger
from app.domain.exceptions import ValueObjectError
from app.domain.repositories import UserRepository
from app.domain.value_objects import UserId, UserRole


class GetUserUseCase(AuthorizeUserUseCase[GetUserInputDTO, GetUserOutputDTO]):
    """Use case for getting a single user by ID."""

    _required_roles: list[UserRole] = [UserRole.ADMIN, UserRole.USER]

    logger = get_logger(__name__)

    @override
    def __init__(
        self,
        auth_service: AuthService,
        uow_factory: Callable[[], UnitOfWork],
    ) -> None:
        """Initialize with dependencies."""
        super().__init__(auth_service=auth_service)
        self._uow_factory = uow_factory

    @override
    async def run(
        self,
        dto: GetUserInputDTO,
        presenter: AuthPresenter[GetUserOutputDTO],
    ) -> None:
        """Retrieve a user by ID from repository."""
        try:
            user_id = UserId.from_str(dto.user_id)
        except (ValueError, ValueObjectError) as e:
            presenter.domain_error(str(e))
            return

        async with self._uow_factory() as uow:
            repo = uow.get_repo(UserRepository)
            user = await repo.get_by_id(user_id)

        if user is None:
            presenter.not_found("User not found")
            return

        user_dto = UserDTO(
            id=str(user.id),
            username=str(user.username),
            role=str(user.role),
            is_active=user.is_active,
        )

        presenter.ok(GetUserOutputDTO(user=user_dto))
