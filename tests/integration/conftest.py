"""Fixtures for integration tests with real database.

This module uses testcontainers to spin up a PostgreSQL instance
and configures the application to use it via environment variables.

Environment variables are loaded from tests/integration/.env.test
via pytest --envfile flag, then DB connection details are overridden
by testcontainer in the setup_test_database fixture.

IMPORTANT: App modules are imported INSIDE fixtures to ensure
env vars are set before any SQLAlchemy initialization occurs.

Architecture (all function-scoped except infrastructure):
- setup_test_database: session scope - creates PostgreSQL testcontainer once
- init_db_schema: session scope - creates DB schema once
- All test users/actors: function scope - maximum isolation and simplicity
"""

import os
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer

from tests.integration.test_data import IntegrationTestUsers


# NO APP IMPORTS AT MODULE LEVEL!
# They must be imported AFTER env vars are set


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Setup PostgreSQL testcontainer and override DB env vars.

    This fixture runs automatically before all tests in the session.
    It starts a PostgreSQL container and overrides DB connection
    environment variables so that the application connects to the
    test database instead of the one specified in .env.test.
    """
    with PostgresContainer("postgres:16", driver="asyncpg") as postgres:
        # Override ONLY database connection parameters
        # (other env vars are loaded from .env.test by pytest-dotenv)
        os.environ["DB_HOST"] = postgres.get_container_host_ip()
        os.environ["DB_PORT"] = str(postgres.get_exposed_port(5432))
        os.environ["DB_PATH"] = postgres.dbname
        os.environ["DB_USER"] = postgres.username
        os.environ["DB_USER_SECRET"] = postgres.password

        yield postgres
        # Container cleanup happens automatically


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_db_schema(setup_test_database):
    """Create database schema using app's engine.

    This runs ONCE per test session.
    It uses the real application engine (which is now configured to
    connect to the testcontainer via environment variables).

    IMPORTANT: Import app modules HERE, after setup_test_database has run.
    """
    # Import INSIDE fixture after env vars are set
    from app.infrastructure.db.sqlalchemy.models.base import Base
    from app.infrastructure.db.sqlalchemy.models.user import UserORM  # noqa: F401
    from app.infrastructure.db.sqlalchemy.models.user_sessions import (  # noqa: F401
        UserSessionORM,
    )
    from app.infrastructure.db.sqlalchemy.setup import get_engine

    engine = get_engine()  # Now reads correct env vars from testcontainer

    # Create schema once
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup after all tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    """Provide DB session for test data setup.

    Changes are committed to make them visible to API endpoints.
    Tables are reset by the reset_tables fixture after each test.
    """
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def reset_tables():
    """Reset user tables after each test.

    After each test:
    1. DROP TABLE user_sessions (due to FK constraint, drop first)
    2. DROP TABLE users
    3. Recreate both tables

    This ensures complete isolation between tests - each test starts
    with empty tables.
    """
    yield  # Test runs here

    # Reset tables after test
    from app.infrastructure.db.sqlalchemy.models.base import Base
    from app.infrastructure.db.sqlalchemy.models.user import UserORM  # noqa: F401
    from app.infrastructure.db.sqlalchemy.models.user_sessions import (  # noqa: F401
        UserSessionORM,
    )
    from app.infrastructure.db.sqlalchemy.setup import get_engine
    from sqlalchemy import text

    engine = get_engine()
    async with engine.begin() as conn:
        # Drop tables (CASCADE handles FK constraints)
        await conn.execute(text("DROP TABLE IF EXISTS user_sessions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))

        # Recreate tables
        await conn.run_sync(Base.metadata.create_all)


# @pytest_asyncio.fixture(autouse=True)
# async def cleanup_test_data():
#     """Clean up test data after each test.

#     Runs after each test to delete users created during the test.
#     Uses known usernames from IntegrationTestUsers.
#     """
#     yield  # Test runs here

#     # Cleanup after test
#     from app.infrastructure.db.sqlalchemy.setup import get_session_factory
#     from app.infrastructure.db.sqlalchemy.models.user import UserORM
#     from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM
#     from sqlalchemy import delete

#     session_factory = get_session_factory()
#     async with session_factory() as session:
#         # Delete all sessions first (foreign key constraint)
#         await session.execute(delete(UserSessionORM))

#         # Delete users created in tests
#         known_usernames = [
#             IntegrationTestUsers.REGULAR_USER.username,
#             IntegrationTestUsers.ADMIN_USER.username,
#             IntegrationTestUsers.INACTIVE_USER.username,
#             IntegrationTestUsers.ACTOR_USER.username,
#             IntegrationTestUsers.ACTOR_ADMIN.username,
#             IntegrationTestUsers.REVOKED_USER.username,
#             IntegrationTestUsers.USER_TO_CREATE.username,
#             IntegrationTestUsers.ADMIN_TO_CREATE.username,
#             "validuser",  # From test_create_user_invalid_password
#             "hashtest",   # From test_create_user_password_is_hashed
#         ]
#         await session.execute(
#             delete(UserORM).where(UserORM.username.in_(known_usernames))
#         )
#         await session.commit()


@pytest.fixture
def password_hasher():
    """Password hasher for tests."""
    from app.infrastructure.security.adapters.services import BcryptHasher

    return BcryptHasher()


@pytest.fixture
def test_id_generator():
    """ID generator for tests."""
    from app.domain.ports import IdGenerator
    from app.domain.value_objects import UserId

    class TestIdGenerator(IdGenerator):
        def new(self) -> UserId:
            return UserId(uuid4())

    return TestIdGenerator()


# ============================================================================
# USER FIXTURES (function-scoped for maximum isolation)
# ============================================================================


@pytest_asyncio.fixture
async def user_to_authenticate(db_session, password_hasher):
    """Regular user for authentication tests.

    User is created from IntegrationTestUsers.REGULAR_USER.
    Cleaned up by cleanup_test_data fixture.
    """
    from app.domain.value_objects import UserRawPassword
    from app.infrastructure.db.sqlalchemy.models.user import UserORM

    user_data = IntegrationTestUsers.REGULAR_USER
    user = UserORM(
        id=uuid4(),
        username=user_data.username,
        password_hash=password_hasher.hash(
            UserRawPassword(user_data.raw_password)
        ).value,
        role=user_data.role,
        is_active=user_data.is_active,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session, password_hasher):
    """Admin user for authentication tests.

    User is created from IntegrationTestUsers.ADMIN_USER.
    Cleaned up by cleanup_test_data fixture.
    """
    from app.domain.value_objects import UserRawPassword
    from app.infrastructure.db.sqlalchemy.models.user import UserORM

    user_data = IntegrationTestUsers.ADMIN_USER
    user = UserORM(
        id=uuid4(),
        username=user_data.username,
        password_hash=password_hasher.hash(
            UserRawPassword(user_data.raw_password)
        ).value,
        role=user_data.role,
        is_active=user_data.is_active,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def inactive_user(db_session, password_hasher):
    """Inactive user for negative authentication tests.

    User is created from IntegrationTestUsers.INACTIVE_USER.
    is_active=False, should fail authentication.
    Cleaned up by cleanup_test_data fixture.
    """
    from app.domain.value_objects import UserRawPassword
    from app.infrastructure.db.sqlalchemy.models.user import UserORM

    user_data = IntegrationTestUsers.INACTIVE_USER
    user = UserORM(
        id=uuid4(),
        username=user_data.username,
        password_hash=password_hasher.hash(
            UserRawPassword(user_data.raw_password)
        ).value,
        role=user_data.role,
        is_active=user_data.is_active,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def user_with_revoked_session(password_hasher, api_client):
    """User with revoked session for authorization tests.

    Creates user, logs in to create session, then revokes the session.
    Returns user + headers + cookies (but session is revoked).

    Note: Uses its own session with commit (not the rollback session)
    to persist changes needed for the test.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select, update
    from app.domain.value_objects import UserRawPassword
    from app.infrastructure.db.sqlalchemy.models.user import UserORM
    from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()

    # Create user
    user_data = IntegrationTestUsers.REGULAR_USER
    async with session_factory() as session:
        user = UserORM(
            id=uuid4(),
            username=user_data.username,
            password_hash=password_hasher.hash(
                UserRawPassword(user_data.raw_password)
            ).value,
            role=user_data.role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        user_id = user.id
        username = user.username

    # Login to create session
    response = await api_client.post(
        "/auth/login",
        data={"username": username, "password": user_data.raw_password},
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    session_id = response.cookies.get("session_id")

    # Revoke session
    async with session_factory() as session:
        from uuid import UUID
        stmt = (
            update(UserSessionORM)
            .where(UserSessionORM.id == UUID(session_id))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await session.execute(stmt)
        await session.commit()

    # Return a dict with user info (not ORM object)
    return {
        "user_id": user_id,
        "username": username,
        "headers": {"Authorization": f"Bearer {token}"},
        "cookies": {"session_id": session_id},
    }


# ============================================================================
# ACTOR FIXTURES (function-scoped for safety and simplicity)
# ============================================================================


@pytest_asyncio.fixture
async def admin_actor(api_client, password_hasher):
    """Admin actor with valid JWT and session_id for authorization tests.

    Creates admin user, logs in, returns authentication credentials.
    Use this fixture when test needs to make authenticated admin requests.

    Note: Uses its own session with commit to persist user for login.

    Returns dict: {"user_id": UUID, "username": str, "headers": {...}, "cookies": {...}}
    """
    from app.domain.value_objects import UserRawPassword
    from app.infrastructure.db.sqlalchemy.models.user import UserORM
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()

    # Create admin from test data
    user_data = IntegrationTestUsers.ADMIN_USER
    async with session_factory() as session:
        admin = UserORM(
            id=uuid4(),
            username=user_data.username,
            password_hash=password_hasher.hash(
                UserRawPassword(user_data.raw_password)
            ).value,
            role=user_data.role,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        admin_id = admin.id
        admin_username = admin.username

    # Login to get JWT and session_id
    response = await api_client.post(
        "/auth/login",
        data={"username": admin_username, "password": user_data.raw_password},
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    session_id = response.cookies.get("session_id")

    return {
        "user_id": admin_id,
        "username": admin_username,
        "headers": {"Authorization": f"Bearer {token}"},
        "cookies": {"session_id": session_id},
    }


@pytest_asyncio.fixture
async def user_actor(api_client, password_hasher):
    """Regular user actor with valid JWT and session_id for authorization tests.

    Creates regular user, logs in, returns authentication credentials.
    Use this fixture when test needs to make authenticated user requests.

    Note: Uses its own session with commit to persist user for login.

    Returns dict: {"user_id": UUID, "username": str, "headers": {...}, "cookies": {...}}
    """
    from app.domain.value_objects import UserRawPassword
    from app.infrastructure.db.sqlalchemy.models.user import UserORM
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()

    # Create user from test data
    user_data = IntegrationTestUsers.REGULAR_USER
    async with session_factory() as session:
        user = UserORM(
            id=uuid4(),
            username=user_data.username,
            password_hash=password_hasher.hash(
                UserRawPassword(user_data.raw_password)
            ).value,
            role=user_data.role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        user_id = user.id
        user_username = user.username

    # Login to get JWT and session_id
    response = await api_client.post(
        "/auth/login",
        data={"username": user_username, "password": user_data.raw_password},
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    session_id = response.cookies.get("session_id")

    return {
        "user_id": user_id,
        "username": user_username,
        "headers": {"Authorization": f"Bearer {token}"},
        "cookies": {"session_id": session_id},
    }


# ============================================================================
# API CLIENT FIXTURE
# ============================================================================


@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide HTTP client for API testing.

    This client connects to the real application, which is configured
    to use the testcontainer database via environment variables.

    NO dependency_overrides are used - this tests the real configuration
    path including UnitOfWork, get_db_session(), and all middleware.
    """
    from app.interface.http.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as client:
        yield client
