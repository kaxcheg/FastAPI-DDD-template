from __future__ import annotations

from typing import Callable, override

from app.application.dto import AuthRequestDTO, AuthResponseDTO
from app.application.ports.presenters import Presenter
from app.application.ports.services import PasswordVerifier
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.base import UseCase
from app.config.logging import get_logger
from app.domain.entities.user.repo import UserRepository
from app.domain.exceptions import ValueObjectError
from app.domain.value_objects import Username, UserRawPassword


class AuthenticateUserUseCase(UseCase[AuthRequestDTO, AuthResponseDTO]):
    """Authenticate user by username and password."""

    logger = get_logger(__name__)

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        password_verifier: PasswordVerifier,
    ) -> None:
        """Initialize with UoW factory and password verifier."""
        self._uow_factory = uow_factory
        self._password_verifier = password_verifier

    @override
    async def execute(
        self,
        dto: AuthRequestDTO,
        presenter: Presenter[AuthResponseDTO],
    ) -> None:
        """Validate credentials and emit auth result."""
        try:
            async with self._uow_factory() as uow:
                repo: UserRepository = uow.get_repo(UserRepository)
                user = await repo.get_by_username(Username(dto.username))
        except ValueObjectError:
            presenter.unauthorized("Invalid credentials")
            self.logger.warning(
                {"event": "auth_failed", "reason": "bad_username_format"}
            )
            return

        if user is None:
            presenter.unauthorized("Invalid credentials")
            self.logger.warning({"event": "auth_failed", "reason": "user_not_found"})
            return

        try:
            ok = self._password_verifier.verify(
                UserRawPassword(dto.raw_password), user.password_hash
            )
        except ValueObjectError:
            presenter.unauthorized("Invalid credentials")
            self.logger.warning(
                {"event": "auth_failed", "reason": "bad_password_format"}
            )
            return

        if not ok:
            presenter.unauthorized("Invalid credentials")
            self.logger.warning({"event": "auth_failed", "reason": "password_mismatch"})
            return

        presenter.ok(
            AuthResponseDTO(
                user_id=str(user.id),
                username=str(user.username),
                role=str(user.role),
            )
        )
        self.logger.info({"event": "auth_succeeded", "user_id": str(user.id)})
