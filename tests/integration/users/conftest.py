"""Fixtures for integration tests with real database.

This module uses testcontainers to spin up a PostgreSQL instance
and configures the application to use it via environment variables.

Environment variables are loaded from tests/integration/.env.test
via pytest --envfile flag, then DB connection details are overridden
by testcontainer in the setup_test_database fixture.

IMPORTANT: App modules are imported INSIDE fixtures to ensure
env vars are set before any SQLAlchemy initialization occurs.

COOKIE HANDLING IN TESTS:
httpx AsyncClient with ASGITransport doesn't automatically persist cookies
from Set-Cookie headers. Use extract_cookies_from_response() helper to
manually extract cookies for use in subsequent requests.
See: https://github.com/encode/httpx/discussions/2144

Architecture (all function-scoped except infrastructure):
- setup_test_database: session scope - creates PostgreSQL testcontainer once
- init_db_schema: session scope - creates DB schema once
- All test users/actors: function scope - maximum isolation and simplicity
"""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID, uuid4

import httpx
import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer
from sqlalchemy import update, text

# NO APP IMPORTS AT MODULE LEVEL!
# ORM models are imported inside fixtures to avoid triggering SQLAlchemy init
# They must be imported AFTER env vars are set

from app.domain.ports import IdGenerator
from app.domain.value_objects import UserId, UserRawPassword

from app.infrastructure.db.sqlalchemy.models.base import Base
from app.infrastructure.db.sqlalchemy.models.user import UserORM  # noqa: F401
from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM  # noqa: F401
from app.infrastructure.db.sqlalchemy.setup import get_session_factory



@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Setup PostgreSQL testcontainer and override DB env vars.

    This fixture runs automatically before all tests in the session.
    It starts a PostgreSQL container and overrides DB connection
    environment variables so that the application connects to the
    test database instead of the one specified in env.test.
    """
    with PostgresContainer("postgres:16", driver="asyncpg") as postgres:
        # Override ONLY database connection parameters
        # (other env vars are loaded from env.test by pytest-dotenv)
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
    from app.infrastructure.db.sqlalchemy.setup import get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        # Drop tables (CASCADE handles FK constraints)
        await conn.execute(text("DROP TABLE IF EXISTS user_sessions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))

        # Recreate tables
        await conn.run_sync(Base.metadata.create_all)

@pytest.fixture
def password_hasher():
    """Password hasher for tests."""
    from app.infrastructure.security.adapters.services import BcryptHasher

    return BcryptHasher()


@pytest.fixture
def test_id_generator():
    """ID generator for tests."""

    class TestIdGenerator(IdGenerator):
        def new(self) -> UserId:
            return UserId(uuid4())

    return TestIdGenerator()


# ============================================================================
# USER FACTORY (for flexible test data creation)
# ============================================================================

@dataclass
class TestUserData:
    """Unified data class for test users."""
    
    user: UserORM
    password: str
    user_id: UUID
    username: str
    role: str
    headers: dict | None = None
    cookies: dict | None = None


async def create_user_with_auth(
    db_session,
    password_hasher,
    api_client=None,
    *,
    username: str = "testuser",
    password: str = "testpass123",
    role: str = "user",
    is_active: bool = True,
    with_auth: bool = False,
) -> TestUserData:
    """Factory: create user in DB with optional auth headers.

    Args:
        db_session: DB session for user creation
        password_hasher: Password hasher
        api_client: API client (required if with_auth=True)
        username: Username (default: "testuser")
        password: Raw password (default: "testpass123")
        role: User role (default: "user")
        is_active: Active status (default: True)
        with_auth: Create JWT + session via login (default: False)

    Returns:
        TestUserData with user ORM, password, headers, cookies
    """
    
    # Create user in DB
    user = UserORM(
        id=uuid4(),
        username=username,
        password_hash=password_hasher.hash(UserRawPassword(password)).value,
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    await db_session.flush()  # Send to DB, generate ID if needed
    await db_session.commit()  # Commit to make visible to API endpoints

    headers = None

    # Optionally create JWT + session via login
    if with_auth:
        if not api_client:
            raise ValueError("api_client required when with_auth=True")

        # Login to get JWT and session_id
        response = await api_client.post(
            "/auth/login",
            data={"username": username, "password": password},
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Login failed for {username}: {response.status_code} {response.text}"
            )

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

    return TestUserData(
        user=user,
        password=password,
        role=role,
        user_id=user.id,
        username=user.username,
        headers=headers,
        cookies=None,
    )


# ============================================================================
# USER FIXTURES (function-scoped for maximum isolation)
# ============================================================================


@pytest_asyncio.fixture
async def user_to_authenticate(db_session, password_hasher) -> TestUserData:
    """Regular user for authentication tests."""
    return await create_user_with_auth(
        db_session,
        password_hasher,
        username="test_user",
        password="user_password",
        role="user",
    )


@pytest_asyncio.fixture
async def user_with_revoked_session(db_session, password_hasher, api_client) -> TestUserData:
    """User with revoked session for authorization tests."""
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    # Create user with auth using factory
    result = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="revoked_user",
        password="revoked_password",
        role="user",
        with_auth=True,
    )

    # Revoke session - extract session_id from JWT
    assert result.headers is not None
    token = result.headers["Authorization"].replace("Bearer ", "")
    decoded = jwt.decode(token, options={"verify_signature": False})
    session_id = decoded["sid"]
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = (
            update(UserSessionORM)
            .where(UserSessionORM.id == UUID(session_id))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await session.execute(stmt)
        await session.commit()

    return result


# ============================================================================
# ACTOR FIXTURES (function-scoped for safety and simplicity)
# ============================================================================


@pytest_asyncio.fixture
async def admin_actor(db_session, password_hasher, api_client) -> TestUserData:
    """Admin actor with valid JWT and session_id."""
    return await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="test_admin",
        password="admin_password",
        role="admin",
        with_auth=True,
    )


@pytest_asyncio.fixture
async def user_actor(db_session, password_hasher, api_client) -> TestUserData:
    """Regular user actor with valid JWT and session_id."""
    return await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="test_user_actor",
        password="user_actor_password",
        role="user",
        with_auth=True,
    )


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


def extract_cookies_from_response(response: httpx.Response) -> httpx.Cookies:
    """Extract cookies from Set-Cookie header for ASGI testing.

    httpx AsyncClient with ASGITransport doesn't automatically persist cookies
    to the client's cookie jar, even though Set-Cookie headers are present.
    This is a known limitation when testing ASGI applications.

    This helper manually parses Set-Cookie headers to extract cookie values
    for use in subsequent test requests.

    References:
    - https://github.com/encode/httpx/discussions/2144
    - https://github.com/encode/httpx/discussions/2825

    Args:
        response: httpx Response object from AsyncClient

    Returns:
        httpx.Cookies object containing extracted cookies

    Example:
        login_response = await api_client.post("/auth/login", ...)
        cookies = extract_cookies_from_response(login_response)
        refresh_response = await api_client.post("/auth/refresh", cookies=cookies)
    """
    cookies = httpx.Cookies()

    # Get all Set-Cookie headers (there may be multiple)
    set_cookie_headers = response.headers.get_list("set-cookie")

    for header_value in set_cookie_headers:
        # Parse: "name=value; Path=/; HttpOnly; Secure; SameSite=lax"
        # We only need the "name=value" part
        cookie_parts = header_value.split(";")
        if cookie_parts:
            name_value = cookie_parts[0].strip()
            if "=" in name_value:
                name, value = name_value.split("=", 1)
                cookies.set(name.strip(), value.strip())

    return cookies
