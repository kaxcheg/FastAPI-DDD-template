"""Django middleware (mirrors FastAPI middleware in main.py)."""

from __future__ import annotations

import traceback
from typing import Awaitable, Callable, Final
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse

from app.config.logging import get_logger
from app.infrastructure.db.django_orm.adapters.services import AuthPayload
from app.infrastructure.security.jwt_service import (
    JwtTokenExpired,
    JwtTokenInvalid,
)
from app.interface.drf.dependencies import get_access_token_service

logger = get_logger(__name__)


PUBLIC_PREFIXES: Final[tuple[str, ...]] = (
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/login",
    "/auth/refresh",
)


class ExceptionHandlerMiddleware:
    """Convert unexpected exceptions to a 500 JSON error and log the trace."""

    async_capable = True
    sync_capable = False

    def __init__(
        self,
        get_response: Callable[[HttpRequest], Awaitable[HttpResponse]],
    ) -> None:
        self.get_response = get_response

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            return await self.get_response(request)
        except Exception as e:
            logger.error(
                {
                    "event": "unhandled_exception",
                    "path": request.path,
                    "method": request.method,
                    "error": str(e),
                    "trace": traceback.format_exc().splitlines(),
                }
            )
            return JsonResponse({"detail": "Internal server error"}, status=500)


class AuthMiddleware:
    """Validate Bearer JWT and attach auth_payload to request."""

    async_capable = True
    sync_capable = False

    def __init__(
        self,
        get_response: Callable[[HttpRequest], Awaitable[HttpResponse]],
    ) -> None:
        self.get_response = get_response

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method == "OPTIONS" or any(
            request.path.startswith(p) for p in PUBLIC_PREFIXES
        ):
            return await self.get_response(request)

        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            access_token_service = get_access_token_service()
            try:
                access_token = access_token_service.decode(
                    auth_header[len("Bearer ") :]
                )
            except (JwtTokenInvalid, JwtTokenExpired):
                return JsonResponse({"detail": "Not authorized."}, status=401)

            user_id = access_token.get("sub")
            sid = access_token.get("sid")
            user_role = access_token.get("role")

            if (
                user_id
                and isinstance(user_id, str)
                and sid
                and isinstance(sid, str)
                and user_role
                and isinstance(user_role, str)
            ):
                request.auth_payload = AuthPayload(  # type: ignore[attr-defined]
                    user_id=UUID(user_id),
                    session_id=UUID(sid),
                    role=user_role,
                )
                return await self.get_response(request)

        return JsonResponse({"detail": "Not authorized."}, status=401)


class CacheControlMiddleware:
    """Set safe Cache-Control policy for successful responses."""

    async_capable = True
    sync_capable = False

    EXCLUDED_PREFIXES: Final = frozenset(
        {"/docs", "/redoc", "/openapi.json", "/health", "/metrics"}
    )

    def __init__(
        self,
        get_response: Callable[[HttpRequest], Awaitable[HttpResponse]],
    ) -> None:
        self.get_response = get_response

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        response = await self.get_response(request)

        if "Cache-Control" in response:
            return response

        path = request.path
        method = request.method.upper()

        if any(path == p or path.startswith(p + "/") for p in self.EXCLUDED_PREFIXES):
            return response

        status_code = response.status_code
        is_success = (200 <= status_code < 300) or status_code == 304
        if not is_success:
            return response

        has_auth_header = "Authorization" in request.headers
        has_req_cookies = bool(request.COOKIES)
        sets_cookie = "Set-Cookie" in response
        if has_auth_header or has_req_cookies or sets_cookie:
            response["Cache-Control"] = "no-store"
            return response

        if method in {"GET", "HEAD"}:
            response["Cache-Control"] = "private, max-age=60"
        else:
            response["Cache-Control"] = "no-store"

        return response
