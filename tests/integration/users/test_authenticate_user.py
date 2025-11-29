"""Integration tests for authentication (login) use case.

These tests verify the authentication flow through real HTTP endpoints.
"""

import pytest
from httpx import AsyncClient

from tests.integration.users.conftest import create_user_with_auth


@pytest.mark.asyncio
async def test_authenticate_user_success(api_client: AsyncClient, user_to_authenticate):
    """Test successful authentication with valid credentials."""
    response = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": user_to_authenticate.password},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_authenticate_admin_success(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test successful authentication as admin user."""
    # Create admin user using factory
    admin_data = await create_user_with_auth(
        db_session,
        password_hasher,
        username="admin_user",
        password="admin_pass123",
        role="admin",
    )

    response = await api_client.post(
        "/auth/login",
        data={"username": admin_data.username, "password": admin_data.password},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


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
    api_client: AsyncClient, user_to_authenticate
):
    """Test authentication fails with incorrect password."""
    response = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": "wrong_password"},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_authenticate_inactive_user(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test authentication fails for inactive user (is_active=False)."""
    # Create inactive user using factory
    inactive_data = await create_user_with_auth(
        db_session,
        password_hasher,
        username="inactive_user",
        password="inactive_pass123",
        role="user",
        is_active=False,
    )

    response = await api_client.post(
        "/auth/login",
        data={"username": inactive_data.username, "password": inactive_data.password},
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
    api_client: AsyncClient, user_to_authenticate
):
    """Test that username is case-sensitive."""
    response = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username.upper(), "password": user_to_authenticate.password},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_authenticate_creates_session_in_db(
    api_client: AsyncClient, user_to_authenticate
):
    """Test that authentication creates a user session in database."""
    from uuid import UUID
    from sqlalchemy import select
    import jwt
    from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    response = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": user_to_authenticate.password},
    )

    assert response.status_code == 200
    # Extract session_id from JWT token
    token = response.json()["access_token"]
    decoded = jwt.decode(token, options={"verify_signature": False})
    session_id = decoded["sid"]

    # Verify session exists in DB
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserSessionORM).where(
            UserSessionORM.id == UUID(session_id)
        )
        result = await session.execute(stmt)
        user_session = result.scalar_one_or_none()

        assert user_session is not None
        assert user_session.user_id == user_to_authenticate.user_id
        assert user_session.revoked_at is None
        assert user_session.expires_at is not None


@pytest.mark.asyncio
async def test_authenticate_multiple_logins_create_multiple_sessions(
    api_client: AsyncClient, user_to_authenticate
):
    """Test that multiple logins create separate sessions."""
    from sqlalchemy import select
    import jwt
    from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    # First login
    response1 = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": user_to_authenticate.password},
    )
    token1 = response1.json()["access_token"]
    decoded1 = jwt.decode(token1, options={"verify_signature": False})
    session_id_1 = decoded1["sid"]

    # Second login
    response2 = await api_client.post(
        "/auth/login",
        data={"username": user_to_authenticate.username, "password": user_to_authenticate.password},
    )
    token2 = response2.json()["access_token"]
    decoded2 = jwt.decode(token2, options={"verify_signature": False})
    session_id_2 = decoded2["sid"]

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert session_id_1 != session_id_2

    # Both sessions should exist in DB
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserSessionORM).where(
            UserSessionORM.user_id == user_to_authenticate.user_id
        )
        result = await session.execute(stmt)
        sessions = result.scalars().all()

        assert len(sessions) >= 2
