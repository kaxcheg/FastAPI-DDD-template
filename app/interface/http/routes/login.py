from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.dto import AuthRequestDTO, AuthResponseDTO
from app.application.ports.presenters import State

from app.interface.http.adapters.presenters import FastAPIAuthenticationPresenter
from app.interface.http.routes.dependencies import get_authenticate_user_uc
from app.interface.http.utils import create_access_token
from app.interface.http.schemas import Token, ErrorResponse
from app.interface.http.utils import raise_for_presenter_400_state

from app.config.logging import setup_logger
# ------------ controller -----------------------------------------------------
router = APIRouter()

@router.post(
        "/login", 
        status_code=200,
        response_model=Token,
        responses=
        {
            401: {"description": "Unauthorized", "model": ErrorResponse},
            422: {"description": "Unprocessable entity", "model": ErrorResponse},
        })
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends(OAuth2PasswordRequestForm)],
    uc:   Annotated[AuthenticateUserUseCase, Depends(get_authenticate_user_uc)],
):
    logger = setup_logger(__name__)

    presenter = FastAPIAuthenticationPresenter()
    dto = AuthRequestDTO(
        username=form.username,
        raw_password=form.password
    )
    await uc.execute(dto, presenter)

    if presenter.state == State.OK and isinstance(presenter.response, AuthResponseDTO):
        token = create_access_token(data={"sub": presenter.response.user_id, "role": presenter.response.role})
        logger.info({
            "event": "token_created",
            "user_id": f"{presenter.response.user_id}"
        })
        return Token(
            access_token=token,
            token_type="Bearer"
        )
    if isinstance(presenter.response, str):
        raise_for_presenter_400_state(presenter)
    