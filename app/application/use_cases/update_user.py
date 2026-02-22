from __future__ import annotations

from typing import Callable, override

from app.application.dto import UpdateUserInputDTO, UpdateUserOutputDTO, UserDTO
from app.application.exceptions import DuplicateUserError
from app.application.ports.presenters import AuthPresenter
from app.application.ports.services import AuthService
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.base import AuthorizeUserUseCase
from app.config.logging import get_logger
from app.domain.entities.user.repo import UserRepository
from app.domain.exceptions import ValueObjectError
from app.domain.exceptions.base import DomainError
from app.domain.value_objects import UserId, Username, UserRole


class UpdateUserUseCase(AuthorizeUserUseCase[UpdateUserInputDTO, UpdateUserOutputDTO]):
    """Use case for updating existing users (admin-only)."""

    _required_roles: list[UserRole] = [UserRole.ADMIN]

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
        dto: UpdateUserInputDTO,
        presenter: AuthPresenter[UpdateUserOutputDTO],
    ) -> None:
        """Validate input, load user, apply changes, persist."""
        try:
            user_id = UserId.from_str(dto.user_id)
        except (ValueError, ValueObjectError) as e:
            presenter.domain_error(str(e))
            return

        if dto.username is None and dto.role is None:
            presenter.bad_request("No fields to update")
            return

        try:
            async with self._uow_factory() as uow:
                repo = uow.get_repo(UserRepository)
                user = await repo.get_by_id(user_id)

                if user is None:
                    presenter.not_found("User not found")
                    return

                try:
                    if dto.username is not None:
                        user.change_username(Username(dto.username))

                    if dto.role is not None:
                        user.change_role(UserRole(dto.role))
                except (DomainError, ValueError) as e:
                    presenter.domain_error(f"User cannot be updated: {e}")
                    return

                await repo.update(user)
        except DuplicateUserError:
            presenter.conflict("Username already exists")
            return

        presenter.ok(
            UpdateUserOutputDTO(
                user=UserDTO(
                    id=str(user.id),
                    username=str(user.username),
                    role=str(user.role),
                    is_active=user.is_active,
                )
            )
        )
        self.logger.info(
            {
                "event": "user_updated",
                "use_case": self.__class__.__name__,
                "user_id": str(user.id),
            }
        )
