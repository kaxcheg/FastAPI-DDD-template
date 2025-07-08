from typing import Callable

from app.application.ports.services import AuthService, PasswordHasher
from app.application.ports.uow import UnitOfWork
from app.domain.entities.user.user import User
from app.domain.services.services import IdGenerator
from app.domain.value_objects import UserRole, Username, UserRawPassword
from app.domain.entities.user.repo import UserRepository
from app.domain.exceptions import ValueObjectError
from app.domain.exceptions.base import DomainError

from app.application.use_cases.base import AuthorizeUserUseCase
from app.application.dto import CreateUserInputDTO, CreateUserOutputDTO
from app.application.ports.presenters import AuthPresenter

from app.config.logging import setup_logger
from app.application.exceptions import DuplicateUserError

class CreateUserUseCase(AuthorizeUserUseCase[CreateUserInputDTO, CreateUserOutputDTO]):
    logger = setup_logger(__name__)

    def __init__(
        self,
        auth_service: AuthService[UserRepository],
        uow_factory: Callable[[], UnitOfWork],
        hasher: PasswordHasher,
        id_gen: IdGenerator
    ) -> None:
        super().__init__(
            auth_service=auth_service, 
            uow_factory=uow_factory, 
            target_role=UserRole.ADMIN
        )
        self._hasher = hasher
        self._id_gen = id_gen
        
    async def run(
            self, 
            dto: CreateUserInputDTO, 
            presenter: AuthPresenter[CreateUserOutputDTO]
            ) -> None:
        
        try:
            raw_password = UserRawPassword(dto.password)    
            pwd_hash = self._hasher.hash(raw_password)
            user = User.create(
                username=Username(dto.username),
                password_hash=pwd_hash,
                role=UserRole(dto.role),
                id_gen=self._id_gen,
            )
        except (DomainError, ValueError) as e:
            presenter.error("User with provided parameters cannot be created.")
            return
        
        try: 
            async with self._uow_factory() as uow:
                uow: UnitOfWork
                repo = uow.get_repo(UserRepository)
                await repo.add(user)
        except DuplicateUserError:
            presenter.conflict(f"Username already exists")
            return
            
        presenter.ok(CreateUserOutputDTO(
            id = str(user.id),
            username=str(user.username),
            role=str(user.role)
        ))
        self.logger.info({
            "event": "user_created",
            "use_case": f"{self.__class__.__name__}",
            "user_id": f"{user.id}",
            })
