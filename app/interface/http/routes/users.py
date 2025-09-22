from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.application.dto import CreateUserInputDTO, CreateUserOutputDTO
from app.application.ports.presenters import State
from app.application.use_cases.create_user import CreateUserUseCase
from app.interface.http.adapters.presenters import FastAPICreateUserPresenter
from app.interface.http.routes.dependencies import get_create_user_uc
from app.interface.http.schemas import (
    CreateUserRequest,
    CreateUserResponse,
    ErrorResponse,
)
from app.interface.http.utils import raise_for_presenter_400_state

router = APIRouter()


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateUserResponse,
    responses={
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        409: {"description": "Conflict", "model": ErrorResponse},
        422: {"description": "Unprocessable entity", "model": ErrorResponse},
    },
)
async def create_user(
    body: CreateUserRequest,
    uc: Annotated[CreateUserUseCase, Depends(get_create_user_uc)],
) -> CreateUserResponse:
    """Create a new user and return its public data."""
    presenter = FastAPICreateUserPresenter()
    await uc.execute(CreateUserInputDTO(**body.model_dump(mode="python")), presenter)

    if presenter.state is State.OK and isinstance(
        presenter.response, CreateUserOutputDTO
    ):
        return CreateUserResponse(**asdict(presenter.response))

    # Always raise for non-OK states to avoid returning None
    if isinstance(presenter.response, str):
        raise_for_presenter_400_state(presenter)
    else:
        raise ValueError("Wrong presenter response type")
