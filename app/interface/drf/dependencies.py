"""DI container for Django DRF interface (mirrors FastAPI dependencies.py)."""

from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from typing import Callable, Protocol

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
from app.infrastructure.db.django_orm.adapters.services import (
    AuthPayload,
    TokenSessionAuthServiceDjango,
)
from app.infrastructure.db.django_orm.adapters.uow import UoWDjango
from app.infrastructure.security.adapters.services import (
    BcryptHasher,
    BcryptPasswordVerifier,
)
from app.infrastructure.security.jwt_service import JwtTokenService
from app.infrastructure.security.random_hex_token_service import RandomHEXTokenService

cfg = get_settings()


class HasAuthPayload(Protocol):
    """Protocol for request objects that carry an auth payload."""

    auth_payload: AuthPayload


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
    return lambda: UoWDjango()


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


def get_auth_service(request: HasAuthPayload) -> AuthService:
    """Return AuthService bound to JWT credentials from request."""
    return TokenSessionAuthServiceDjango(
        payload=request.auth_payload,
        uow_factory=get_uow_factory(),
    )


def get_create_user_uc(request: HasAuthPayload) -> CreateUserUseCase:
    """Return CreateUser use case with injected ports."""
    return CreateUserUseCase(
        auth_service=get_auth_service(request),
        uow_factory=get_uow_factory(),
        hasher=get_hasher(),
    )


def get_all_users_uc(request: HasAuthPayload) -> GetAllUsersUseCase:
    """Return GetAllUsers use case with injected ports."""
    return GetAllUsersUseCase(
        auth_service=get_auth_service(request),
        uow_factory=get_uow_factory(),
    )


def get_user_uc(request: HasAuthPayload) -> GetUserUseCase:
    """Return GetUser use case with injected ports."""
    return GetUserUseCase(
        auth_service=get_auth_service(request),
        uow_factory=get_uow_factory(),
    )


def get_update_user_uc(request: HasAuthPayload) -> UpdateUserUseCase:
    """Return UpdateUser use case with injected ports."""
    return UpdateUserUseCase(
        auth_service=get_auth_service(request),
        uow_factory=get_uow_factory(),
    )


def get_change_password_uc(request: HasAuthPayload) -> ChangePasswordUseCase:
    """Return ChangePassword use case with injected ports."""
    return ChangePasswordUseCase(
        auth_service=get_auth_service(request),
        uow_factory=get_uow_factory(),
        hasher=get_hasher(),
    )


def get_delete_user_uc(request: HasAuthPayload) -> DeleteUserUseCase:
    """Return DeleteUser use case with injected ports."""
    return DeleteUserUseCase(
        auth_service=get_auth_service(request),
        uow_factory=get_uow_factory(),
    )
