from datetime import timedelta
from functools import lru_cache
from typing import Annotated, AsyncIterator, Callable

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.services import AuthService, PasswordHasher, PasswordVerifier
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.create_user import CreateUserUseCase
from app.config import get_settings
from app.domain.ports.services import IdGenerator
from app.infrastructure.db.sqlalchemy.adapters.services import (
    TokenSessionAuthService,
    UUIDv4Generator,
)
from app.infrastructure.db.sqlalchemy.adapters.uow import (
    UoWSQL,
)
from app.infrastructure.db.sqlalchemy.setup import get_session_factory
from app.infrastructure.db.sqlalchemy.user_session_service import UserSessionService
from app.infrastructure.security.adapters.services import (
    BcryptHasher,
    BcryptPasswordVerifier,
)
from app.infrastructure.security.jwt_service import JwtTokenService

cfg = get_settings()


@lru_cache
def get_jwt_service() -> JwtTokenService:
    """Return a cached JwtTokenService instance."""
    return JwtTokenService(
        secret=cfg.JWT_SECRET,
        algorithm=cfg.JWT_ALGORITHM,
        default_expires=timedelta(minutes=cfg.JWT_TOKEN_EXPIRY_TIME),
        required_claims=("sub", "exp", "role", "sid"),
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


def get_user_session_service(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserSessionService:
    """Return UserSessionService with injected DB session."""
    return UserSessionService(
        db_session=db_session, expiry_time=cfg.SESSION_EXPIRY_TIME
    )


@lru_cache
def get_uow_factory() -> Callable[[], UnitOfWork]:
    """Return factory that creates a new UnitOfWork per call."""
    return lambda: UoWSQL(session_factory=get_session_factory())


@lru_cache
def get_hasher() -> PasswordHasher:
    """Return password hasher implementation."""
    return BcryptHasher()


@lru_cache
def get_id_gen() -> IdGenerator:
    """Return identifier generator implementation."""
    return UUIDv4Generator()


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
    user_session_service: Annotated[
        UserSessionService, Depends(get_user_session_service)
    ],
) -> AuthService:
    """Return AuthService bound to JWT credentials."""

    return TokenSessionAuthService(
        payload=request.state.auth_payload, user_session_service=user_session_service
    )


def get_create_user_uc(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    hasher: Annotated[PasswordHasher, Depends(get_hasher)],
    id_gen: Annotated[IdGenerator, Depends(get_id_gen)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> CreateUserUseCase:
    """Return CreateUser use case with injected ports."""
    return CreateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=hasher,
        id_gen=id_gen,
    )
