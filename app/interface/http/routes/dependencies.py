from typing import Callable, Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.application.dto import CredentialDTO
from app.application.ports.uow import UnitOfWork
from app.application.ports.services import PasswordHasher, AuthService, PasswordVerifier
from app.application.use_cases.create_user import CreateUserUseCase
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.domain.services.services import IdGenerator
from app.infrastructure.db.sqlalchemy.adapters import UUIDv4Generator, UoWSQL
from app.infrastructure.db.sqlalchemy.setup import async_session_factory
from app.infrastructure.security.adapters import BcryptHasher, BcryptPasswordVerifier
from app.interface.http.adapters.auth import TokenSQLAuthService

from app.config.config import settings

security = HTTPBearer()

def get_uow_factory() -> Callable[[], UoWSQL]:
    """Фабрика-поставщик: каждый вызов выдаёт новый UoW."""
    return lambda: UoWSQL(session_factory=async_session_factory)

def get_hasher() -> BcryptHasher:
    return BcryptHasher()

def get_id_gen() -> UUIDv4Generator:
    return UUIDv4Generator()

def get_verifier() -> BcryptPasswordVerifier:
    return BcryptPasswordVerifier()

def get_authenticate_user_uc(
        uow_factory: Callable[[], UnitOfWork] = Depends(get_uow_factory),
        password_verifier: PasswordVerifier = Depends(get_verifier)
) -> AuthenticateUserUseCase:
    return AuthenticateUserUseCase(
        uow_factory=uow_factory,
        password_verifier=password_verifier
    )

def get_token_auth_service(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    dto = CredentialDTO(
        scheme="bearer",
        value=credentials.credentials
    )
    auth_service = TokenSQLAuthService(credentials=dto)
    return auth_service

def get_create_user_uc(
    uow_factory: Callable[[], UnitOfWork] = Depends(get_uow_factory),
    hasher: PasswordHasher = Depends(get_hasher),
    id_gen: IdGenerator = Depends(get_id_gen),
    auth_service: AuthService = Depends(get_token_auth_service)
) -> CreateUserUseCase:
    """Отдаёт готовый CreateUserUseCase со всеми портами."""
    return CreateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=hasher,
        id_gen=id_gen,
    )