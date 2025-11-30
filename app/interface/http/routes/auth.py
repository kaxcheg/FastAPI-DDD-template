from typing import Annotated, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Request
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
from app.interface.http.adapters.presenters import FastAPIPresenter
from app.interface.http.routes.dependencies import (
    get_authenticate_user_uc,
    get_jwt_service,
    get_uow_factory,
)
from app.interface.http.schemas import ErrorResponse, Token
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
    token_service: Annotated[JwtTokenService, Depends(get_jwt_service)],
) -> Token:
    """Authenticate user and return a JWT access token.

    Args:
        form: OAuth2 username/password form.
        uc: AuthenticateUser use case instance.
        token_service: JWT service for token issuing.

    Returns:
        Token: Bearer access token on success.
    """
    presenter = FastAPIPresenter[AuthResponseDTO]()
    dto = AuthRequestDTO(username=form.username, raw_password=form.password)
    await uc.execute(dto, presenter)

    if presenter.state is State.OK and isinstance(presenter.response, AuthResponseDTO):
        user_id = presenter.response.user_id
        async with uow_factory() as uow:
            user_session_repo = uow.get_repo(UserSessionORMRepo)
            user_session = await user_session_repo.create(
                user_id=UUID(user_id),
                expiry_time=cfg.SESSION_EXPIRY_TIME,
                max_sessions=cfg.MAX_CONCURRENT_SESSIONS,
            )
            token = token_service.issue(
                claims={
                    "sub": user_id,
                    "role": presenter.response.role,
                    "sid": str(user_session.id),
                }
            )
        logger.info(
            {
                "event": "login",
                "user_id": f"{presenter.response.user_id}",
                "session_id": str(user_session.id),
            }
        )

        return Token(access_token=token, token_type="Bearer")

    # Always raise on non-OK states
    if isinstance(presenter.response, str):
        raise_for_presenter_400_state(presenter)
    else:
        raise ValueError("Wrong presenter response type")


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    uow_factory: Annotated[Callable[[], UnitOfWork], Depends(get_uow_factory)],
) -> None:
    """Revoke current session and clear cookie."""
    auth: AuthPayload = request.state.auth_payload

    async with uow_factory() as uow:
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
