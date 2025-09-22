from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.application.dto import AuthRequestDTO, AuthResponseDTO
from app.application.ports.presenters import State
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.config.logging import get_logger
from app.infrastructure.security.jwt_service import JwtTokenService
from app.interface.http.adapters.presenters import FastAPIAuthenticationPresenter
from app.interface.http.routes.dependencies import (
    get_authenticate_user_uc,
    get_jwt_service,
)
from app.interface.http.schemas import ErrorResponse, Token
from app.interface.http.utils import raise_for_presenter_400_state

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/login",
    status_code=200,
    response_model=Token,
    responses={
        401: {"description": "Unauthorized", "model": ErrorResponse},
        422: {"description": "Unprocessable entity", "model": ErrorResponse},
    },
)
async def login(
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
    presenter = FastAPIAuthenticationPresenter()
    dto = AuthRequestDTO(username=form.username, raw_password=form.password)
    await uc.execute(dto, presenter)

    if presenter.state is State.OK and isinstance(presenter.response, AuthResponseDTO):
        token = token_service.issue(
            claims={"sub": presenter.response.user_id, "role": presenter.response.role}
        )
        logger.info(
            {"event": "token_created", "user_id": f"{presenter.response.user_id}"}
        )
        return Token(access_token=token, token_type="Bearer")

    # Always raise on non-OK states
    if isinstance(presenter.response, str):
        raise_for_presenter_400_state(presenter)
    else:
        raise ValueError("Wrong presenter response type")
