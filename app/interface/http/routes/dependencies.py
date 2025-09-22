from datetime import timedelta
from functools import lru_cache
from typing import Annotated, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.dto import CredentialDTO
from app.application.ports.services import AuthService, PasswordHasher, PasswordVerifier
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.create_user import CreateUserUseCase
from app.config import get_settings
from app.domain.entities.user.repo import UserRepository
from app.domain.services.services import IdGenerator
from app.infrastructure.db.sqlalchemy.adapters import (
    TokenSQLAuthService,
    UoWSQL,
    UUIDv4Generator,
)
from app.infrastructure.db.sqlalchemy.setup import get_session_factory
from app.infrastructure.security.adapters import BcryptHasher, BcryptPasswordVerifier
from app.infrastructure.security.jwt_service import JwtTokenService

security: HTTPBearer = HTTPBearer()


@lru_cache
def get_jwt_service() -> JwtTokenService:
    """Return a cached JwtTokenService instance."""
    cfg = get_settings()
    return JwtTokenService(
        secret=cfg.FASTAPI_DDD_TEMPLATE_JWT_SECRET,
        algorithm=cfg.FASTAPI_DDD_TEMPLATE_JWT_ALGORITHM,
        default_expires=timedelta(
            minutes=cfg.FASTAPI_DDD_TEMPLATE_JWT_TOKEN_EXPIRY_TIME
        ),
        required_claims=("sub", "exp", "role"),
    )


def get_uow_factory() -> Callable[[], UnitOfWork]:
    """Return factory that creates a new UnitOfWork per call."""
    return lambda: UoWSQL(session_factory=get_session_factory())


def get_hasher() -> PasswordHasher:
    """Return password hasher implementation."""
    return BcryptHasher()


def get_id_gen() -> IdGenerator:
    """Return identifier generator implementation."""
    return UUIDv4Generator()


def get_verifier() -> PasswordVerifier:
    """Return password verifier implementation."""
    return BcryptPasswordVerifier()


def get_authenticate_user_uc(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    password_verifier: Annotated[PasswordVerifier, Depends(get_verifier)],
) -> AuthenticateUserUseCase:
    """Return AuthenticateUser use case with injected ports."""
    return AuthenticateUserUseCase(
        uow_factory=uow_factory,
        password_verifier=password_verifier,
    )


def get_auth_service(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> AuthService[UserRepository]:
    """Return AuthService bound to JWT credentials."""

    return TokenSQLAuthService(
        credentials=CredentialDTO(scheme="bearer", value=credentials.credentials),
        token_service=get_jwt_service(),
    )


def get_create_user_uc(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    hasher: Annotated[PasswordHasher, Depends(get_hasher)],
    id_gen: Annotated[IdGenerator, Depends(get_id_gen)],
    auth_service: Annotated[AuthService[UserRepository], Depends(get_auth_service)],
) -> CreateUserUseCase:
    """Return CreateUser use case with injected ports."""
    return CreateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=hasher,
        id_gen=id_gen,
    )
