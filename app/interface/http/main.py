from __future__ import annotations

import traceback
from typing import Awaitable, Callable, Final
from uuid import UUID

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.config.logging import get_logger
from app.infrastructure.db.sqlalchemy.adapters.services import AuthPayload
from app.infrastructure.security.jwt_service import (
    JwtTokenExpired,
    JwtTokenInvalid,
    JwtTokenService,
)
from app.interface.http.routes import login, users
from app.interface.http.routes.dependencies import get_jwt_service

logger = get_logger(__name__)  # Reuse module-level logger.


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""

    app = FastAPI(title="dddapitpl")
    app.include_router(users.router, prefix="/users", tags=["Users"])
    app.include_router(login.router, prefix="/auth", tags=["Authentication"])
    return app


app = create_app()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],  # Swagger UI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="dddapitpl",
        version="0.0.1",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }

    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]


@app.get("/health", tags=["Health"])
def healthcheck() -> dict[str, str]:
    """Return simple health status."""
    return {"status": "ok"}


@app.middleware("http")
async def catch_unhandled_exceptions_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Convert unexpected exceptions to a 500 JSON error and log the trace."""
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(
            {
                "event": "unhandled_exception",
                "path": request.url.path,
                "method": request.method,
                "error": str(e),
                "trace": traceback.format_exc().splitlines(),
            }
        )
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )


PUBLIC_PREFIXES = ("/docs", "/openapi.json", "/redoc", "/health", "/auth/login")


@app.middleware("http")
async def check_user_auth_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Check if user session is expired."""
    if request.method == "OPTIONS" or any(
        request.url.path.startswith(p) for p in PUBLIC_PREFIXES
    ):
        return await call_next(request)

    sid_cookie = request.cookies.get("session_id")
    auth_header = request.headers.get("Authorization", "")

    if sid_cookie and auth_header.startswith("Bearer "):
        token_service: JwtTokenService = get_jwt_service()
        try:
            token = token_service.decode(auth_header[len("Bearer ") :])
        except (JwtTokenInvalid, JwtTokenExpired):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authorized."},
            )

        user_id = token.get("sub")
        sid = token.get("sid")
        user_role = token.get("role")
        if (
            user_id
            and isinstance(user_id, str)
            and sid
            and isinstance(sid, str)
            and sid == sid_cookie
            and user_role
            and isinstance(user_role, str)
        ):
            request.state.auth_payload = AuthPayload(
                user_id=UUID(user_id),
                session_id=UUID(sid),
                role=user_role,
            )

            return await call_next(request)

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Not authorized."}
    )


@app.middleware("http")
async def cache_control_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Set safe Cache-Control policy for successful responses."""
    EXCLUDED_PREFIXES: Final[set[str]] = {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/metrics",
    }

    response: Response = await call_next(request)

    # Respect explicit Cache-Control set by handlers.
    if "cache-control" in (k.lower() for k in response.headers.keys()):
        return response

    path = request.url.path
    method = request.method.upper()

    # Skip excluded prefixes.
    is_excluded = any(path == p or path.startswith(p + "/") for p in EXCLUDED_PREFIXES)
    if is_excluded:
        return response

    # Apply only to successful responses (2xx, 304).
    status = response.status_code
    is_success = (200 <= status < 300) or status == 304
    if not is_success:
        return response

    # Prevent storing authenticated or cookie-bearing responses.
    has_auth_header = "authorization" in request.headers
    has_req_cookies = bool(request.cookies)
    sets_cookie = "set-cookie" in (k.lower() for k in response.headers.keys())
    if has_auth_header or has_req_cookies or sets_cookie:
        response.headers["Cache-Control"] = "no-store"
        return response

    # Cache safe idempotent responses briefly; forbid storing others.
    if method in {"GET", "HEAD"}:
        response.headers["Cache-Control"] = "private, max-age=60"
    else:
        response.headers["Cache-Control"] = "no-store"

    return response
