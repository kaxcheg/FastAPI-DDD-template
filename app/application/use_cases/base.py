from typing import Generic, TypeVar, Any, Protocol, final, Callable

from app.domain.value_objects import UserRole
from app.domain.entities.user.repo import UserRepository
from app.application.ports.services import AuthService
from app.application.dto.base import DTO
from app.application.ports.presenters import Presenter
from app.application.ports import AuthPresenter, UnitOfWork
from app.domain.exceptions.base import DomainError
from app.application.exceptions import NotAuthenticatedError, NotAuthorizedError
from app.config.logging import setup_logger
I = TypeVar("I", bound=DTO, contravariant=True)
O = TypeVar("O", bound=DTO)

class UseCase(Protocol[I, O]):
    async def execute(self, dto: I, presenter: Presenter[O]) -> None: ...

class AuthorizeUserUseCase(Protocol[I, O]):
    _auth: AuthService[UserRepository]
    _target_role: UserRole
    _uow_factory: Callable[[], UnitOfWork]

    logger = setup_logger(__name__)

    def __init__(
            self, 
            uow_factory: Callable[[], UnitOfWork],
            auth_service: AuthService[UserRepository], 
            target_role: UserRole
        ) -> None:
        self._uow_factory = uow_factory
        self._auth = auth_service
        self._target_role = target_role
    
    @final
    async def execute(self, dto: I, presenter: AuthPresenter[O]) -> None:
        try:
            async with self._uow_factory() as uow:
                uow: UnitOfWork
                user_repo = uow.get_repo(UserRepository)
                user = await self._auth.current_user(user_repo)
        except (NotAuthenticatedError, DomainError):
            presenter.unauthorized("Not authorized")
            return
        
        try:
            self._auth.ensure_role(user.id, user.role, self._target_role)
        except NotAuthorizedError:
            presenter.forbidden("Forbidden")
            self.logger.warning({
                "event": "access_denied",
                "reason": "Insufficient role permissions",
                "use_case": f"{self.__class__.__name__}",
                "user_id": f"{user.id}"
            })
            return    

        await self.run(dto, presenter)

    async def run(self, dto: I, presenter: AuthPresenter[O]) -> None: ...