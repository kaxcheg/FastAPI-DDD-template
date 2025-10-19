from __future__ import annotations

import traceback
from typing import Awaitable, Callable, Final

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.config.logging import get_logger
from app.interface.http.routes import login, users

logger = get_logger(__name__)  # Reuse module-level logger.


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""

    app = FastAPI(title="FastAPI DDD template")
    app.include_router(users.router, tags=["User"])
    app.include_router(login.router, tags=["Login"])
    return app


app = create_app()


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
