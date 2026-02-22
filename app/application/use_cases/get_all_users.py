from __future__ import annotations

from typing import Callable, override

from app.application.dto import GetAllUsersInputDTO, GetAllUsersOutputDTO, UserDTO
from app.application.ports.presenters import AuthPresenter
from app.application.ports.services import AuthService
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.base import AuthorizeUserUseCase
from app.config.logging import get_logger
from app.domain.repositories import UserRepository
from app.domain.value_objects import UserRole


class GetAllUsersUseCase(
    AuthorizeUserUseCase[GetAllUsersInputDTO, GetAllUsersOutputDTO]
):
    """Use case for getting all users (admin-only)."""

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
        dto: GetAllUsersInputDTO,
        presenter: AuthPresenter[GetAllUsersOutputDTO],
    ) -> None:
        """Retrieve all users from repository."""
        async with self._uow_factory() as uow:
            repo = uow.get_repo(UserRepository)
            users = await repo.get_all()

            user_dtos = [
                UserDTO(
                    id=str(user.id),
                    username=str(user.username),
                    role=str(user.role),
                    is_active=user.is_active,
                )
                for user in users
            ]

        presenter.ok(GetAllUsersOutputDTO(users=user_dtos))
