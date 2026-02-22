from __future__ import annotations

from typing import Callable, override

from app.application.dto import CreateUserInputDTO, CreateUserOutputDTO
from app.application.ports.presenters import AuthPresenter
from app.application.ports.services import AuthService, PasswordHasher
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.base import AuthorizeUserUseCase
from app.config.logging import get_logger
from app.domain.entities.user.user import User
from app.domain.exceptions import DuplicateUsernameError
from app.domain.exceptions.base import DomainError
from app.domain.repositories import UserRepository
from app.domain.services import UserInvariantService
from app.domain.value_objects import Username, UserRawPassword, UserRole


class CreateUserUseCase(AuthorizeUserUseCase[CreateUserInputDTO, CreateUserOutputDTO]):
    """Use case for creating new users (admin-only)."""

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
        dto: CreateUserInputDTO,
        presenter: AuthPresenter[CreateUserOutputDTO],
    ) -> None:
        """Validate input and create user in repository."""
        try:
            raw_password = UserRawPassword(dto.password)
            pwd_hash = self._hasher.hash(raw_password)
            user = User.create(
                username=Username(dto.username),
                password_hash=pwd_hash,
                role=UserRole(dto.role),
            )
        except (DomainError, ValueError) as e:
            presenter.domain_error(f"User cannot be created: {e}")
            return

        try:
            async with self._uow_factory() as uow:
                repo = uow.get_repo(UserRepository)
                invariant = UserInvariantService(repo)
                await invariant.ensure_username_unique(user.username)
                await repo.add(user)
        except DuplicateUsernameError:
            presenter.conflict("Username already exists")
            return

        presenter.ok(
            CreateUserOutputDTO(
                id=str(user.id),
                username=str(user.username),
                role=str(user.role),
            )
        )
        self.logger.info(
            {
                "event": "user_created",
                "use_case": self.__class__.__name__,
                "user_id": str(user.id),
            }
        )
