"""DRF views for /auth endpoints (mirrors FastAPI routes/auth.py)."""

from __future__ import annotations

from typing import Callable
from uuid import UUID

from adrf.views import APIView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from app.application.dto import AuthRequestDTO, AuthResponseDTO
from app.application.ports.presenters import State
from app.application.ports.uow import UnitOfWork
from app.config import get_settings
from app.config.logging import get_logger
from app.infrastructure.db.django_orm.adapters.services import AuthPayload
from app.infrastructure.db.django_orm.user_session_repo import UserSessionDjangoRepo
from app.interface.drf.adapters.presenters import DRFPresenter
from app.interface.drf.dependencies import (
    get_access_token_service,
    get_authenticate_user_uc,
    get_refresh_token_service,
    get_uow_factory,
)
from app.interface.drf.serializers import (
    ErrorSerializer,
    LoginRequestSerializer,
    RefreshTokenRequestSerializer,
    TokenSerializer,
)
from app.interface.drf.utils import raise_for_presenter_state

cfg = get_settings()
logger = get_logger(__name__)


class LoginView(APIView):
    """POST /auth/login — authenticate and issue tokens."""

    @extend_schema(
        request=LoginRequestSerializer,
        responses={200: TokenSerializer, 403: ErrorSerializer},
    )
    async def post(self, request: Request) -> Response:
        """Authenticate user and return access + refresh tokens."""
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uc = get_authenticate_user_uc()
        uow_factory: Callable[[], UnitOfWork] = get_uow_factory()
        access_token_service = get_access_token_service()
        refresh_token_service = get_refresh_token_service()

        presenter = DRFPresenter[AuthResponseDTO]()
        dto = AuthRequestDTO(
            username=serializer.validated_data["username"],
            raw_password=serializer.validated_data["password"],
        )
        await uc.execute(dto, presenter)

        if presenter.state is State.OK and isinstance(
            presenter.response, AuthResponseDTO
        ):
            user_id = presenter.response.user_id

            refresh_token = refresh_token_service.generate()
            refresh_token_hash = refresh_token_service.hash(refresh_token)

            async with uow_factory() as uow:
                uow: UnitOfWork
                session_repo = uow.get_repo(UserSessionDjangoRepo)
                user_session = await session_repo.create(
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

            data = {
                "access_token": access_token,
                "access_token_type": "Bearer",
                "expires_in": cfg.JWT_TOKEN_EXPIRY * 60,
                "refresh_token": refresh_token,
                "refresh_expires_in": cfg.REFRESH_TOKEN_EXPIRY * 60,
            }
            out = TokenSerializer(data)
            return Response(out.data, status=status.HTTP_200_OK)

        if isinstance(presenter.response, str):
            raise_for_presenter_state(presenter)
        raise ValueError("Wrong presenter response type")


class RefreshView(APIView):
    """POST /auth/refresh — rotate tokens."""

    @extend_schema(
        request=RefreshTokenRequestSerializer,
        responses={200: TokenSerializer, 401: ErrorSerializer},
    )
    async def post(self, request: Request) -> Response:
        """Exchange refresh token for new access + refresh tokens."""
        serializer = RefreshTokenRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uow_factory: Callable[[], UnitOfWork] = get_uow_factory()
        access_token_service = get_access_token_service()
        refresh_token_service = get_refresh_token_service()

        refresh_token: str = serializer.validated_data["refresh_token"]

        async with uow_factory() as uow:
            uow: UnitOfWork
            session_repo = uow.get_repo(UserSessionDjangoRepo)
            user_orm, user_session = (
                await session_repo.get_user_valid_session_by_refresh_token(
                    refresh_token_hash=refresh_token_service.hash(refresh_token)
                )
            )
            if user_session is None or user_orm is None:
                return Response(
                    {"detail": "Not authorized."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            new_refresh_token = refresh_token_service.generate()
            new_refresh_token_hash = refresh_token_service.hash(new_refresh_token)

            await session_repo.rotate_refresh_token(
                session=user_session,
                new_refresh_token_hash=new_refresh_token_hash,
                expiry_time=cfg.SESSION_EXPIRY_TIME,
            )

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

        data = {
            "access_token": new_access_token,
            "access_token_type": "Bearer",
            "expires_in": cfg.JWT_TOKEN_EXPIRY * 60,
            "refresh_token": new_refresh_token,
            "refresh_expires_in": cfg.REFRESH_TOKEN_EXPIRY * 60,
        }
        out = TokenSerializer(data)
        return Response(out.data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /auth/logout — revoke current session."""

    @extend_schema(
        request=None,
        responses={204: None},
    )
    async def post(self, request: Request) -> Response:
        """Revoke current session."""
        auth: AuthPayload = request.auth_payload  # type: ignore[attr-defined]

        uow_factory: Callable[[], UnitOfWork] = get_uow_factory()

        async with uow_factory() as uow:
            uow: UnitOfWork
            session_repo = uow.get_repo(UserSessionDjangoRepo)
            revoked = await session_repo.revoke(auth.session_id)

        if revoked:
            logger.info(
                {
                    "event": "logout",
                    "user_id": str(auth.user_id),
                    "session_id": str(auth.session_id),
                }
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
