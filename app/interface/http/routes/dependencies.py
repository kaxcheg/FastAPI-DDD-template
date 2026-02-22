from datetime import timedelta
from functools import lru_cache
from typing import Annotated, Callable

from fastapi import Depends, Request

from app.application.ports.services import AuthService, PasswordHasher, PasswordVerifier
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.change_password import ChangePasswordUseCase
from app.application.use_cases.create_user import CreateUserUseCase
from app.application.use_cases.delete_user import DeleteUserUseCase
from app.application.use_cases.get_all_users import GetAllUsersUseCase
from app.application.use_cases.get_user import GetUserUseCase
from app.application.use_cases.update_user import UpdateUserUseCase
from app.config import get_settings
from app.infrastructure.db.sqlalchemy.adapters.services import (
    TokenSessionAuthService,
)
from app.infrastructure.db.sqlalchemy.adapters.uow import (
    UoWSQL,
)
from app.infrastructure.db.sqlalchemy.setup import get_session_factory
from app.infrastructure.security.adapters.services import (
    BcryptHasher,
    BcryptPasswordVerifier,
)
from app.infrastructure.security.jwt_service import JwtTokenService
from app.infrastructure.security.random_hex_token_service import RandomHEXTokenService

cfg = get_settings()


@lru_cache
def get_access_token_service() -> JwtTokenService:
    """Return JWT service for short-lived access tokens."""
    return JwtTokenService(
        secret=cfg.JWT_SECRET,
        algorithm=cfg.JWT_ALGORITHM,
        default_expires=timedelta(minutes=cfg.JWT_TOKEN_EXPIRY),
        required_claims=("sub", "exp", "role", "sid"),
    )


@lru_cache
def get_refresh_token_service() -> RandomHEXTokenService:
    """Return service for generating/hashing refresh tokens."""
    return RandomHEXTokenService(token_length=cfg.REFRESH_TOKEN_LENGTH)


@lru_cache
def get_uow_factory() -> Callable[[], UnitOfWork]:
    """Return factory that creates a new UnitOfWork per call."""
    return lambda: UoWSQL(session_factory=get_session_factory())


@lru_cache
def get_hasher() -> PasswordHasher:
    """Return password hasher implementation."""
    return BcryptHasher()


@lru_cache
def get_verifier() -> PasswordVerifier:
    """Return password verifier implementation."""
    return BcryptPasswordVerifier()


@lru_cache
def get_authenticate_user_uc() -> AuthenticateUserUseCase:
    """Return AuthenticateUser use case with injected ports."""
    return AuthenticateUserUseCase(
        uow_factory=get_uow_factory(),
        password_verifier=get_verifier(),
    )


def get_auth_service(
    request: Request,
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
) -> AuthService:
    """Return AuthService bound to JWT credentials."""

    return TokenSessionAuthService(
        payload=request.state.auth_payload, uow_factory=uow_factory
    )


def get_create_user_uc(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    hasher: Annotated[PasswordHasher, Depends(get_hasher)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> CreateUserUseCase:
    """Return CreateUser use case with injected ports."""
    return CreateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=hasher,
    )


def get_all_users_uc(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> GetAllUsersUseCase:
    """Return GetAllUsers use case with injected ports."""
    return GetAllUsersUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )


def get_user_uc(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> GetUserUseCase:
    """Return GetUser use case with injected ports."""
    return GetUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )


def get_update_user_uc(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UpdateUserUseCase:
    """Return UpdateUser use case with injected ports."""
    return UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )


def get_change_password_uc(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    hasher: Annotated[PasswordHasher, Depends(get_hasher)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ChangePasswordUseCase:
    """Return ChangePassword use case with injected ports."""
    return ChangePasswordUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=hasher,
    )


def get_delete_user_uc(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> DeleteUserUseCase:
    """Return DeleteUser use case with injected ports."""
    return DeleteUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )
