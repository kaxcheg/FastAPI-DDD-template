from typing import Callable

from app.domain.value_objects import Username, UserRawPassword
from app.domain.entities.user.repo import UserRepository
from app.domain.exceptions import ValueObjectError
from app.application.ports.services import PasswordVerifier
from app.application.ports.uow import UnitOfWork
from app.application.dto import AuthRequestDTO, AuthResponseDTO
from app.application.ports.presenters import Presenter
from app.application.use_cases.base import UseCase


class AuthenticateUserUseCase(UseCase[AuthRequestDTO, AuthResponseDTO]):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        password_verifier: PasswordVerifier
    ):
        self._uow_factory = uow_factory
        self._password_verifier = password_verifier

    async def execute(
        self,
        dto: AuthRequestDTO,
        presenter: Presenter[AuthResponseDTO]
    ) -> None:

        try:
            async with self._uow_factory() as uow:
                uow: UnitOfWork
                repo = uow.get_repo(UserRepository)
                user = await repo.get_by_username(Username(dto.username))
        except ValueObjectError:
            presenter.unauthorized("Invalid credentials")
            return
        
        if user is None:
            presenter.unauthorized("Invalid credentials")
            return

        try:
            if not self._password_verifier.verify(
                    raw_password=UserRawPassword(dto.raw_password), 
                    hashed_password=user.password_hash
                ):
                presenter.unauthorized("Invalid credentials")
                return
        except ValueObjectError:
            presenter.unauthorized("Invalid credentials")
            return

        presenter.ok(
            AuthResponseDTO(
                user_id=str(user.id),
                username=str(user.username),
                role = str(user.role)
            ))