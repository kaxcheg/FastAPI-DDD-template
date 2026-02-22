from __future__ import annotations

from typing import Callable, override

from app.application.dto import ChangePasswordInputDTO, ChangePasswordOutputDTO, UserDTO
from app.application.ports.presenters import AuthPresenter
from app.application.ports.services import AuthService, PasswordHasher
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.base import AuthorizeUserUseCase
from app.config.logging import get_logger
from app.domain.exceptions import ValueObjectError
from app.domain.exceptions.base import DomainError
from app.domain.repositories import UserRepository
from app.domain.value_objects import UserId, UserRawPassword, UserRole


class ChangePasswordUseCase(
    AuthorizeUserUseCase[ChangePasswordInputDTO, ChangePasswordOutputDTO]
):
    """Use case for changing a user's password (admin-only)."""

    _required_roles: list[UserRole] = [UserRole.ADMIN]

    logger = get_logger(__name__)

    @override
    def __init__(
        self,
        auth_service: AuthService,
        uow_factory: Callable[[], UnitOfWork],
        hasher: PasswordHasher,
    ) -> None:
        """Initialize with dependencies."""
        super().__init__(auth_service=auth_service)
        self._uow_factory = uow_factory
        self._hasher = hasher

    @override
    async def run(
        self,
        dto: ChangePasswordInputDTO,
        presenter: AuthPresenter[ChangePasswordOutputDTO],
    ) -> None:
        """Validate input, load user, change password, persist."""
        try:
            user_id = UserId.from_str(dto.user_id)
        except (ValueError, ValueObjectError) as e:
            presenter.domain_error(str(e))
            return

        try:
            raw_password = UserRawPassword(dto.new_password)
            pwd_hash = self._hasher.hash(raw_password)
        except (DomainError, ValueError) as e:
            presenter.domain_error(f"Password cannot be changed: {e}")
            return

        async with self._uow_factory() as uow:
            repo = uow.get_repo(UserRepository)
            user = await repo.get_by_id(user_id)

            if user is None:
                presenter.not_found("User not found")
                return

            try:
                user.change_password(pwd_hash)
                await repo.update(user)
            except DomainError as e:
                presenter.domain_error(f"Password cannot be changed: {e}")
                return

        presenter.ok(
            ChangePasswordOutputDTO(
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
                "event": "password_changed",
                "use_case": self.__class__.__name__,
                "user_id": str(user.id),
            }
        )
