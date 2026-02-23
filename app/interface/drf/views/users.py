"""DRF views for /users endpoints (mirrors FastAPI routes/users.py)."""

from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from adrf.views import APIView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from app.application.dto import (
    ChangePasswordInputDTO,
    ChangePasswordOutputDTO,
    CreateUserInputDTO,
    CreateUserOutputDTO,
    DeleteUserInputDTO,
    DeleteUserOutputDTO,
    GetAllUsersInputDTO,
    GetAllUsersOutputDTO,
    GetUserInputDTO,
    GetUserOutputDTO,
    UpdateUserInputDTO,
    UpdateUserOutputDTO,
)
from app.application.ports.presenters import State
from app.interface.drf.adapters.presenters import DRFAuthPresenter
from app.interface.drf.dependencies import (
    get_all_users_uc,
    get_change_password_uc,
    get_create_user_uc,
    get_delete_user_uc,
    get_update_user_uc,
    get_user_uc,
)
from app.interface.drf.serializers import (
    ChangePasswordRequestSerializer,
    ChangePasswordResponseSerializer,
    CreateUserRequestSerializer,
    CreateUserResponseSerializer,
    DeleteUserResponseSerializer,
    ErrorSerializer,
    GetAllUsersResponseSerializer,
    GetUserResponseSerializer,
    UpdateUserRequestSerializer,
    UpdateUserResponseSerializer,
)
from app.interface.drf.utils import raise_for_presenter_state


class UserListView(APIView):
    """GET /users — list all users; POST /users — create user."""

    @extend_schema(
        operation_id="users_list",
        request=None,
        responses={200: GetAllUsersResponseSerializer, 401: ErrorSerializer},
    )
    async def get(self, request: Request) -> Response:
        """Get all users (admin only)."""
        uc = get_all_users_uc(request)  # type: ignore[arg-type]
        presenter = DRFAuthPresenter[GetAllUsersOutputDTO]()
        await uc.execute(GetAllUsersInputDTO(), presenter)

        if presenter.state is State.OK and isinstance(
            presenter.response, GetAllUsersOutputDTO
        ):
            data = {"users": [asdict(user) for user in presenter.response.users]}
            serializer = GetAllUsersResponseSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        raise_for_presenter_state(presenter)

    @extend_schema(
        request=CreateUserRequestSerializer,
        responses={201: CreateUserResponseSerializer, 400: ErrorSerializer},
    )
    async def post(self, request: Request) -> Response:
        """Create a new user (admin only)."""
        serializer = CreateUserRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uc = get_create_user_uc(request)  # type: ignore[arg-type]
        presenter = DRFAuthPresenter[CreateUserOutputDTO]()
        await uc.execute(CreateUserInputDTO(**serializer.validated_data), presenter)

        if presenter.state is State.OK and isinstance(
            presenter.response, CreateUserOutputDTO
        ):
            out = CreateUserResponseSerializer(asdict(presenter.response))
            return Response(out.data, status=status.HTTP_201_CREATED)

        raise_for_presenter_state(presenter)


class UserDetailView(APIView):
    """GET /users/{user_id}; PATCH /users/{user_id}; DELETE /users/{user_id}."""

    @extend_schema(
        operation_id="users_retrieve",
        request=None,
        responses={200: GetUserResponseSerializer, 404: ErrorSerializer},
    )
    async def get(self, request: Request, user_id: UUID) -> Response:
        """Get a single user by ID."""
        uc = get_user_uc(request)  # type: ignore[arg-type]
        presenter = DRFAuthPresenter[GetUserOutputDTO]()
        await uc.execute(GetUserInputDTO(user_id=str(user_id)), presenter)

        if presenter.state is State.OK and isinstance(
            presenter.response, GetUserOutputDTO
        ):
            data = {"user": asdict(presenter.response.user)}
            serializer = GetUserResponseSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        raise_for_presenter_state(presenter)

    @extend_schema(
        request=UpdateUserRequestSerializer,
        responses={200: UpdateUserResponseSerializer, 400: ErrorSerializer},
    )
    async def patch(self, request: Request, user_id: UUID) -> Response:
        """Update an existing user (admin only)."""
        serializer = UpdateUserRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uc = get_update_user_uc(request)  # type: ignore[arg-type]
        presenter = DRFAuthPresenter[UpdateUserOutputDTO]()
        await uc.execute(
            UpdateUserInputDTO(
                user_id=str(user_id),
                username=serializer.validated_data.get("username"),
                role=serializer.validated_data.get("role"),
            ),
            presenter,
        )

        if presenter.state is State.OK and isinstance(
            presenter.response, UpdateUserOutputDTO
        ):
            data = {"user": asdict(presenter.response.user)}
            out = UpdateUserResponseSerializer(data)
            return Response(out.data, status=status.HTTP_200_OK)

        raise_for_presenter_state(presenter)

    @extend_schema(
        request=None,
        responses={200: DeleteUserResponseSerializer, 404: ErrorSerializer},
    )
    async def delete(self, request: Request, user_id: UUID) -> Response:
        """Soft-delete (deactivate) a user (admin only)."""
        uc = get_delete_user_uc(request)  # type: ignore[arg-type]
        presenter = DRFAuthPresenter[DeleteUserOutputDTO]()
        await uc.execute(DeleteUserInputDTO(user_id=str(user_id)), presenter)

        if presenter.state is State.OK and isinstance(
            presenter.response, DeleteUserOutputDTO
        ):
            data = {"user": asdict(presenter.response.user)}
            out = DeleteUserResponseSerializer(data)
            return Response(out.data, status=status.HTTP_200_OK)

        raise_for_presenter_state(presenter)


class ChangePasswordView(APIView):
    """PATCH /users/{user_id}/password — change password."""

    @extend_schema(
        request=ChangePasswordRequestSerializer,
        responses={200: ChangePasswordResponseSerializer, 400: ErrorSerializer},
    )
    async def patch(self, request: Request, user_id: UUID) -> Response:
        """Change a user's password (admin only)."""
        serializer = ChangePasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uc = get_change_password_uc(request)  # type: ignore[arg-type]
        presenter = DRFAuthPresenter[ChangePasswordOutputDTO]()
        await uc.execute(
            ChangePasswordInputDTO(
                user_id=str(user_id),
                new_password=serializer.validated_data["new_password"],
            ),
            presenter,
        )

        if presenter.state is State.OK and isinstance(
            presenter.response, ChangePasswordOutputDTO
        ):
            data = {"user": asdict(presenter.response.user)}
            out = ChangePasswordResponseSerializer(data)
            return Response(out.data, status=status.HTTP_200_OK)

        raise_for_presenter_state(presenter)
