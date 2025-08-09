import traceback

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.interface.http.routes import users, login
from app.config.logging import get_logger, configure_logging

logger = get_logger(__name__)  # Reuse module-level logger.


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    configure_logging()

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
async def catch_unhandled_exceptions_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger = setup_logger(__name__)
        logger.error({
            "event": "unhandled_exception",
            "path": request.url.path,
            "method": request.method,
            "error": str(e),
            "trace": traceback.format_exc().splitlines()
        })
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

@app.middleware("http")
async def cache_control_middleware(request: Request, call_next):
    EXCLUDED_PREFIXES = {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/metrics",
    }
    response: Response = await call_next(request)

    path = request.url.path
    method = request.method

    is_excluded = any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in EXCLUDED_PREFIXES
    )

    if not is_excluded and response.status_code < 400:
        if method == "GET":
            response.headers["Cache-Control"] = "private, max-age=60"
        else:
            response.headers["Cache-Control"] = "no-store"

    return response