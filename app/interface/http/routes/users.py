from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.application.dto import (
    CreateUserInputDTO,
    CreateUserOutputDTO,
    GetAllUsersInputDTO,
    GetAllUsersOutputDTO,
    GetUserInputDTO,
    GetUserOutputDTO,
)
from app.application.ports.presenters import State
from app.application.use_cases.create_user import CreateUserUseCase
from app.application.use_cases.get_all_users import GetAllUsersUseCase
from app.application.use_cases.get_user import GetUserUseCase
from app.interface.http.adapters.presenters import FastAPIAuthPresenter
from app.interface.http.routes.dependencies import (
    get_all_users_uc,
    get_create_user_uc,
    get_user_uc,
)
from app.interface.http.schemas import (
    CreateUserRequest,
    CreateUserResponse,
    ErrorResponse,
    GetAllUsersResponse,
    GetUserResponse,
    UserResponse,
)
from app.interface.http.utils import raise_for_presenter_400_state

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK, response_model=GetAllUsersResponse)
async def get_all_users(
    uc: Annotated[GetAllUsersUseCase, Depends(get_all_users_uc)],
) -> GetAllUsersResponse:
    """Get all users (admin only)."""
    presenter = FastAPIAuthPresenter[GetAllUsersOutputDTO]()
    await uc.execute(GetAllUsersInputDTO(), presenter)

    if presenter.state is State.OK and isinstance(
        presenter.response, GetAllUsersOutputDTO
    ):
        return GetAllUsersResponse(
            users=[UserResponse(**asdict(user)) for user in presenter.response.users]
        )

    if isinstance(presenter.response, str):
        raise_for_presenter_400_state(presenter)
    else:
        raise ValueError("Wrong presenter response type")


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=GetUserResponse,
    responses={
        404: {"description": "Not found", "model": ErrorResponse},
        422: {"description": "Unprocessable entity", "model": ErrorResponse},
    },
)
async def get_user(
    user_id: str,
    uc: Annotated[GetUserUseCase, Depends(get_user_uc)],
) -> GetUserResponse:
    """Get a single user by ID."""
    presenter = FastAPIAuthPresenter[GetUserOutputDTO]()
    await uc.execute(GetUserInputDTO(user_id=user_id), presenter)

    if presenter.state is State.OK and isinstance(presenter.response, GetUserOutputDTO):
        return GetUserResponse(user=UserResponse(**asdict(presenter.response.user)))

    if isinstance(presenter.response, str):
        raise_for_presenter_400_state(presenter)
    else:
        raise ValueError("Wrong presenter response type")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateUserResponse,
    responses={
        409: {"description": "Conflict", "model": ErrorResponse},
        422: {"description": "Unprocessable entity", "model": ErrorResponse},
    },
)
async def create_user(
    body: CreateUserRequest,
    uc: Annotated[CreateUserUseCase, Depends(get_create_user_uc)],
) -> CreateUserResponse:
    """Create a new user and return its public data."""
    presenter = FastAPIAuthPresenter[CreateUserOutputDTO]()
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
