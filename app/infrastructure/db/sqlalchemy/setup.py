from functools import lru_cache

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings


@lru_cache
def get_engine():
    """Lazy singleton async engine."""
    cfg = get_settings()
    return create_async_engine(
        str(cfg.DB_URL),
        connect_args={"server_settings": {"search_path": "app,public"}},
        echo=False,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory():
    """Lazy singleton session factory (bound to engine)."""
    return async_sessionmaker(
        get_engine(),
        expire_on_commit=False,
    )
