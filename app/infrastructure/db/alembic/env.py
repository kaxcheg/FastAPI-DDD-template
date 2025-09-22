import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config

from app.config import get_settings
from app.infrastructure.db.sqlalchemy.models.base import Base  # metadata scan
from app.infrastructure.db.sqlalchemy.models.user import (  # noqa: F401  # ensure model import
    UserORM,
)

settings = get_settings()
config = context.config
config.set_main_option("sqlalchemy.url", str(settings.DB_URL))
config.set_main_option("version_table_schema", str(settings.DB_TABLE_SCHEMA))

if config.config_file_name:
    fileConfig(config.config_file_name)

# metadata for autogeneration
target_metadata = Base.metadata  # type: ignore[attr-defined]


def run_migrations_offline() -> None:
    """Generate SQL migration script without an active DB connection."""

    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        version_table_schema=settings.DB_TABLE_SCHEMA,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def _configure_connection(connection: Connection) -> None:
    """Configure Alembic context for an open SQLAlchemy connection."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=settings.DB_TABLE_SCHEMA,
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,  # set True if your models specify schema
    )


def _do_run_migrations(connection: Connection) -> None:
    """Run migrations inside a transaction using *connection*."""

    _configure_connection(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create async engine, set search_path once, then run migrations."""

    engine: AsyncEngine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with engine.connect() as conn:  # type: ignore[async-context-manager]
        # Set search_path in its own committed txn to survive outer ROLLBACK.
        await conn.execute(text("SET search_path TO app, public"))
        await conn.commit()

        await conn.run_sync(_do_run_migrations)

    await engine.dispose()


def run_migrations_online() -> None:
    """Entry point for *online* migrations (invoked by Alembic)."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
