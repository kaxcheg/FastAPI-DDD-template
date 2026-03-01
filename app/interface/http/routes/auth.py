from typing import Annotated, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.application.dto import AuthRequestDTO, AuthResponseDTO
from app.application.ports.presenters import State
from app.application.ports.uow import UnitOfWork
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.config import get_settings
from app.config.logging import get_logger
from app.infrastructure.db.sqlalchemy.adapters.services import AuthPayload
from app.infrastructure.db.sqlalchemy.user_session_repo import UserSessionORMRepo
from app.infrastructure.security.jwt_service import JwtTokenService
from app.infrastructure.security.random_hex_token_service import RandomHEXTokenService
from app.interface.http.adapters.presenters import FastAPIPresenter
from app.interface.http.routes.dependencies import (
    get_access_token_service,
    get_authenticate_user_uc,
    get_refresh_token_service,
    get_uow_factory,
)
from app.interface.http.schemas import ErrorResponse, RefreshTokenRequest, Token
from app.interface.http.utils import raise_for_presenter_400_state

router = APIRouter()
cfg = get_settings()
logger = get_logger(__name__)


@router.post(
    "/login",
    status_code=200,
    response_model=Token,
    responses={
        422: {"description": "Unprocessable entity", "model": ErrorResponse},
    },
)
async def login(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    form: Annotated[OAuth2PasswordRequestForm, Depends(OAuth2PasswordRequestForm)],
    uc: Annotated[AuthenticateUserUseCase, Depends(get_authenticate_user_uc)],
    access_token_service: Annotated[JwtTokenService, Depends(get_access_token_service)],
    refresh_token_service: Annotated[
        RandomHEXTokenService, Depends(get_refresh_token_service)
    ],
) -> Token:
    """Authenticate user and return access + refresh tokens.

    Both tokens are returned in JSON response for all clients.
    Clients can choose how to store tokens (sessionStorage, memory, etc.).

    Args:
        form: OAuth2 username/password form.
        uc: AuthenticateUser use case instance.
        access_token_service: JWT service for access tokens.
        refresh_token_service: Service for refresh tokens.

    Returns:
        Token: Bearer access token + refresh token.
    """
    presenter = FastAPIPresenter[AuthResponseDTO]()
    dto = AuthRequestDTO(username=form.username, raw_password=form.password)
    await uc.execute(dto, presenter)

    if presenter.state is State.OK and isinstance(presenter.response, AuthResponseDTO):
        user_id = presenter.response.user_id

        # Generate tokens
        refresh_token = refresh_token_service.generate()
        refresh_token_hash = refresh_token_service.hash(refresh_token)

        async with uow_factory() as uow:
            uow: UnitOfWork
            user_session_repo = uow.get_repo(UserSessionORMRepo)
            user_session = await user_session_repo.create(
                user_id=UUID(user_id),
                expiry_time=cfg.SESSION_EXPIRY_TIME,
                max_sessions=cfg.MAX_CONCURRENT_SESSIONS,
                refresh_token_hash=refresh_token_hash,
            )

            access_token = access_token_service.issue(
                claims={
                    "sub": user_id,
                    "role": presenter.response.role,
                    "sid": str(user_session.id),
                }
            )

        logger.info(
            {
                "event": "login",
                "user_id": user_id,
                "session_id": str(user_session.id),
            }
        )

        # Return both tokens in JSON for all clients
        return Token(
            access_token=access_token,
            access_token_type="Bearer",
            expires_in=cfg.JWT_TOKEN_EXPIRY * 60,
            refresh_token=refresh_token,
            refresh_expires_in=cfg.REFRESH_TOKEN_EXPIRY * 60,
        )

    # Always raise on non-OK states
    if isinstance(presenter.response, str):
        raise_for_presenter_400_state(presenter)
    else:
        raise ValueError("Wrong presenter response type")


@router.post(
    "/refresh",
    status_code=200,
    response_model=Token,
    responses={
        422: {"description": "Unprocessable entity", "model": ErrorResponse},
    },
)
async def refresh(
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
    access_token_service: Annotated[JwtTokenService, Depends(get_access_token_service)],
    refresh_token_service: Annotated[
        RandomHEXTokenService, Depends(get_refresh_token_service)
    ],
    body: RefreshTokenRequest,
) -> Token:
    """Exchange refresh token for new access + refresh tokens.

    Implements token rotation: old refresh token is invalidated, new pair issued.
    Both tokens are returned in JSON response for all clients.

    Args:
        uow_factory: Unit of work factory.
        access_token_service: JWT service for access tokens.
        refresh_token_service: Service for refresh tokens.
        body: Refresh token from JSON body.

    Returns:
        Token: New access token + refresh token pair.

    Raises:
        HTTPException 401: If refresh token is invalid/expired/revoked.
    """
    refresh_token = body.refresh_token

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized.",
        )

    async with uow_factory() as uow:
        uow: UnitOfWork
        user_session_repo = uow.get_repo(UserSessionORMRepo)
        user_orm, user_session = (
            await user_session_repo.get_user_valid_session_by_refresh_token(
                refresh_token_hash=refresh_token_service.hash(refresh_token)
            )
        )
        if user_session is None or user_orm is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorized.",
            )

        # Generate new token pair (rotation)
        new_refresh_token = refresh_token_service.generate()
        new_refresh_token_hash = refresh_token_service.hash(new_refresh_token)

        # Rotate refresh token in DB
        await user_session_repo.rotate_refresh_token(
            session=user_session,
            new_refresh_token_hash=new_refresh_token_hash,
            expiry_time=cfg.SESSION_EXPIRY_TIME,
        )

        # Issue new access token
        new_access_token = access_token_service.issue(
            claims={
                "sub": str(user_orm.id),
                "role": user_orm.role,
                "sid": str(user_session.id),
            }
        )

        logger.info(
            {
                "event": "token_refresh",
                "user_id": str(user_orm.id),
                "session_id": str(user_session.id),
            }
        )

    # Return both tokens in JSON for all clients
    return Token(
        access_token=new_access_token,
        access_token_type="Bearer",
        expires_in=cfg.JWT_TOKEN_EXPIRY * 60,
        refresh_token=new_refresh_token,
        refresh_expires_in=cfg.REFRESH_TOKEN_EXPIRY * 60,
    )


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
) -> None:
    """Revoke current session.

    Args:
        request: FastAPI request (contains auth payload).
        uow_factory: Unit of work factory.
    """
    auth: AuthPayload = request.state.auth_payload

    async with uow_factory() as uow:
        uow: UnitOfWork
        user_session_repo = uow.get_repo(UserSessionORMRepo)
        revoked = await user_session_repo.revoke(auth.session_id)

    if revoked:
        logger.info(
            {
                "event": "logout",
                "user_id": str(auth.user_id),
                "session_id": str(auth.session_id),
            }
        )
