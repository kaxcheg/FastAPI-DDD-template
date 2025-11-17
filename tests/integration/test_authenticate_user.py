"""Integration tests for authentication (login) use case.

These tests verify the authentication flow through real HTTP endpoints,
similar to tests/unit/application/test_authenticate_user.py but at integration level.
"""

import pytest
from httpx import AsyncClient

from app.infrastructure.db.sqlalchemy.models.user import UserORM
from tests.integration.test_data import IntegrationTestUsers


@pytest.mark.asyncio
async def test_authenticate_user_success(api_client: AsyncClient, user_to_authenticate: UserORM):
    """Test successful authentication with valid credentials."""
    user_data = IntegrationTestUsers.REGULAR_USER

    response = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": user_data.raw_password},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert "session_id" in response.cookies


@pytest.mark.asyncio
async def test_authenticate_admin_success(api_client: AsyncClient, admin_user: UserORM):
    """Test successful authentication as admin user."""
    user_data = IntegrationTestUsers.ADMIN_USER

    response = await api_client.post(
        "/auth/login",
        data={"username": admin_user.username, "password": user_data.raw_password},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "session_id" in response.cookies


@pytest.mark.asyncio
async def test_authenticate_invalid_username(api_client: AsyncClient):
    """Test authentication fails with non-existent username."""
    response = await api_client.post(
        "/auth/login",
        data={"username": "nonexistent", "password": "password123"},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_authenticate_invalid_password(
    api_client: AsyncClient, user_to_authenticate: UserORM
):
    """Test authentication fails with incorrect password."""
    response = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": "wrong_password"},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_authenticate_inactive_user(api_client: AsyncClient, inactive_user: UserORM):
    """Test authentication fails for inactive user (is_active=False)."""
    user_data = IntegrationTestUsers.INACTIVE_USER

    response = await api_client.post(
        "/auth/login",
        data={"username": inactive_user.username, "password": user_data.raw_password},
    )

    assert response.status_code == 401
    data = response.json()
    assert "Not authorized" in data["detail"]


@pytest.mark.asyncio
async def test_authenticate_empty_credentials(api_client: AsyncClient):
    """Test authentication fails with empty credentials."""
    response = await api_client.post(
        "/auth/login",
        data={"username": "", "password": ""},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticate_case_sensitive_username(
    api_client: AsyncClient, user_to_authenticate: UserORM
):
    """Test that username is case-sensitive."""
    user_data = IntegrationTestUsers.REGULAR_USER

    response = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username.upper(), "password": user_data.raw_password},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_authenticate_creates_session_in_db(
    api_client: AsyncClient, user_to_authenticate: UserORM
):
    """Test that authentication creates a user session in database."""
    from uuid import UUID
    from sqlalchemy import select
    from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    user_data = IntegrationTestUsers.REGULAR_USER

    response = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": user_data.raw_password},
    )

    assert response.status_code == 200
    session_id = response.cookies.get("session_id")
    assert session_id is not None

    # Verify session exists in DB
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserSessionORM).where(
            UserSessionORM.id == UUID(session_id)
        )
        result = await session.execute(stmt)
        user_session = result.scalar_one_or_none()

        assert user_session is not None
        assert user_session.user_id == user_to_authenticate.id
        assert user_session.revoked_at is None
        assert user_session.expires_at is not None


@pytest.mark.asyncio
async def test_authenticate_session_cookie_attributes(
    api_client: AsyncClient, user_to_authenticate: UserORM
):
    """Test that session cookie has correct security attributes."""
    user_data = IntegrationTestUsers.REGULAR_USER

    response = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": user_data.raw_password},
    )

    assert response.status_code == 200

    # Check cookie attributes
    set_cookie = response.headers.get("set-cookie", "")
    assert "session_id=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "samesite=lax" in set_cookie.lower()


@pytest.mark.asyncio
async def test_authenticate_multiple_logins_create_multiple_sessions(
    api_client: AsyncClient, user_to_authenticate: UserORM
):
    """Test that multiple logins create separate sessions."""
    from sqlalchemy import select
    from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    user_data = IntegrationTestUsers.REGULAR_USER

    # First login
    response1 = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": user_data.raw_password},
    )
    session_id_1 = response1.cookies.get("session_id")

    # Second login
    response2 = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": user_data.raw_password},
    )
    session_id_2 = response2.cookies.get("session_id")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert session_id_1 != session_id_2

    # Both sessions should exist in DB
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserSessionORM).where(
            UserSessionORM.user_id == user_to_authenticate.id
        )
        result = await session.execute(stmt)
        sessions = result.scalars().all()

        assert len(sessions) >= 2
