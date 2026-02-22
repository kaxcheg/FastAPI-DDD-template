from __future__ import annotations

from typing import Callable, override

from app.application.dto import DeleteUserInputDTO, DeleteUserOutputDTO, UserDTO
from app.application.ports.presenters import AuthPresenter
from app.application.ports.services import AuthService
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.base import AuthorizeUserUseCase
from app.config.logging import get_logger
from app.domain.exceptions import SelfDeletionError, ValueObjectError
from app.domain.exceptions.base import DomainError
from app.domain.repositories import UserRepository
from app.domain.services import UserInvariantService
from app.domain.value_objects import UserId, UserRole


class DeleteUserUseCase(AuthorizeUserUseCase[DeleteUserInputDTO, DeleteUserOutputDTO]):
    """Use case for soft-deleting (deactivating) a user (admin-only)."""

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
        dto: DeleteUserInputDTO,
        presenter: AuthPresenter[DeleteUserOutputDTO],
    ) -> None:
        """Validate input, check invariants, deactivate user, persist."""
        try:
            target_id = UserId.from_str(dto.user_id)
        except (ValueError, ValueObjectError) as e:
            presenter.domain_error(str(e))
            return

        current_user = await self._auth.current_user()

        try:
            UserInvariantService.ensure_not_self_deletion(current_user.id, target_id)
        except SelfDeletionError:
            presenter.bad_request("Admin cannot delete themselves")
            return

        async with self._uow_factory() as uow:
            repo = uow.get_repo(UserRepository)
            user = await repo.get_by_id(target_id)

            if user is None:
                presenter.not_found("User not found")
                return

            try:
                user.deactivate()
                await repo.update(user)
            except DomainError as e:
                presenter.domain_error(f"User cannot be deleted: {e}")
                return

        presenter.ok(
            DeleteUserOutputDTO(
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
                "event": "user_deleted",
                "use_case": self.__class__.__name__,
                "user_id": str(user.id),
            }
        )
