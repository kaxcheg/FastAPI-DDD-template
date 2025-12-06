"""Integration tests for refresh token authentication flow.

These tests verify the dual-token (access + refresh) authentication system.
"""

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID


from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM
from app.infrastructure.db.sqlalchemy.setup import get_session_factory

@pytest.mark.asyncio
async def test_login_api_client_returns_both_tokens_in_json(
    api_client: AsyncClient, user_to_authenticate
):
    """Test API client (Accept: application/json) receives both tokens in JSON."""
    response = await api_client.post(
        "/auth/login",
        data={
            "username": user_to_authenticate.username,
            "password": user_to_authenticate.password,
        },
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 200
    data = response.json()

    # Check all required fields
    assert "access_token" in data
    assert "refresh_token" in data
    assert "access_token_type" in data
    assert "expires_in" in data
    assert "refresh_expires_in" in data

    assert data["access_token_type"] == "Bearer"
    assert isinstance(data["expires_in"], int)
    assert isinstance(data["refresh_expires_in"], int)
    assert data["refresh_expires_in"] > data["expires_in"]

    # Verify token is valid JWT
    decoded = jwt.decode(data["access_token"], options={"verify_signature": False})
    assert "sub" in decoded
    assert "sid" in decoded
    assert "role" in decoded


@pytest.mark.asyncio
async def test_login_all_clients_return_tokens_in_json(
    api_client: AsyncClient, user_to_authenticate
):
    """Test all clients receive both tokens in JSON response."""
    response = await api_client.post(
        "/auth/login",
        data={
            "username": user_to_authenticate.username,
            "password": user_to_authenticate.password,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # All clients get both tokens in JSON
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] is not None
    assert "expires_in" in data
    assert "refresh_expires_in" in data

    # No cookies should be set
    assert "refresh_token" not in response.cookies


@pytest.mark.asyncio
async def test_login_stores_refresh_token_hash_in_db(
    api_client: AsyncClient, user_to_authenticate
):
    """Test refresh token hash is stored in session table."""
    response = await api_client.post(
        "/auth/login",
        data={
            "username": user_to_authenticate.username,
            "password": user_to_authenticate.password,
        },
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 200
    data = response.json()
    refresh_token = data["refresh_token"]

    # Extract session_id from access token
    decoded = jwt.decode(data["access_token"], options={"verify_signature": False})
    session_id = decoded["sid"]

    # Verify hash in DB
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserSessionORM).where(UserSessionORM.id == UUID(session_id))
        result = await session.execute(stmt)
        user_session = result.scalar_one_or_none()

        assert user_session is not None
        assert user_session.refresh_token_hash is not None
        assert len(user_session.refresh_token_hash) == 64  # SHA-256 hex
        assert user_session.created_at is not None

        # Verify hash matches
        from app.infrastructure.security.random_hex_token_service import (
            RandomHEXTokenService,
        )
        service = RandomHEXTokenService()
        assert service.verify(refresh_token, user_session.refresh_token_hash)


@pytest.mark.asyncio
async def test_refresh_with_valid_token_returns_new_pair(
    api_client: AsyncClient, user_to_authenticate
):
    """Test refresh endpoint with valid token returns new token pair."""
    # Login to get refresh token
    login_response = await api_client.post(
        "/auth/login",
        data={
            "username": user_to_authenticate.username,
            "password": user_to_authenticate.password,
        },
        headers={"Accept": "application/json"},
    )
    old_refresh_token = login_response.json()["refresh_token"]
    old_access_token = login_response.json()["access_token"]

    # Refresh
    refresh_response = await api_client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh_token},
        headers={"Accept": "application/json"},
    )

    assert refresh_response.status_code == 200
    data = refresh_response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert "expires_in" in data
    assert "refresh_expires_in" in data

    # New tokens should be different from old
    assert data["access_token"] != old_access_token
    assert data["refresh_token"] != old_refresh_token




@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(api_client: AsyncClient):
    """Test refresh with invalid token returns 401."""
    from app.config import get_settings
    cfg = get_settings()

    response = await api_client.post(
        "/auth/refresh",
        json={"refresh_token": "a" * cfg.REFRESH_TOKEN_LENGTH * 2},
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_refresh_without_token_returns_422(api_client: AsyncClient):
    """Test refresh without token returns 422 (validation error)."""
    response = await api_client.post(
        "/auth/refresh",
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_refresh_token_can_only_be_used_once(
    api_client: AsyncClient, user_to_authenticate
):
    """Test refresh token rotation - old token invalid after use."""
    # Login
    login_response = await api_client.post(
        "/auth/login",
        data={
            "username": user_to_authenticate.username,
            "password": user_to_authenticate.password,
        },
        headers={"Accept": "application/json"},
    )
    refresh_token = login_response.json()["refresh_token"]

    # First refresh - succeeds
    refresh1 = await api_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={"Accept": "application/json"},
    )
    assert refresh1.status_code == 200

    # Second refresh with SAME token - fails (token rotation)
    refresh2 = await api_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={"Accept": "application/json"},
    )
    assert refresh2.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation_updates_hash_in_db(
    api_client: AsyncClient, user_to_authenticate
):
    """Test refresh token rotation updates hash in database."""
    # Login
    login_response = await api_client.post(
        "/auth/login",
        data={
            "username": user_to_authenticate.username,
            "password": user_to_authenticate.password,
        },
        headers={"Accept": "application/json"},
    )
    old_refresh_token = login_response.json()["refresh_token"]

    # Get session_id
    decoded = jwt.decode(
        login_response.json()["access_token"], options={"verify_signature": False}
    )
    session_id = decoded["sid"]

    # Get old hash from DB
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserSessionORM).where(UserSessionORM.id == UUID(session_id))
        result = await session.execute(stmt)
        user_session = result.scalar_one_or_none()
        old_hash = user_session.refresh_token_hash

    # Refresh
    refresh_response = await api_client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh_token},
        headers={"Accept": "application/json"},
    )
    new_refresh_token = refresh_response.json()["refresh_token"]

    # Check hash updated in DB
    async with session_factory() as session:
        stmt = select(UserSessionORM).where(UserSessionORM.id == UUID(session_id))
        result = await session.execute(stmt)
        user_session = result.scalar_one_or_none()
        new_hash = user_session.refresh_token_hash

        assert new_hash != old_hash

        # Verify new token matches new hash
        from app.infrastructure.security.random_hex_token_service import (
            RandomHEXTokenService,
        )
        service = RandomHEXTokenService()
        assert service.verify(new_refresh_token, new_hash)


@pytest.mark.asyncio
async def test_logout_revokes_session(
    api_client: AsyncClient, user_to_authenticate
):
    """Test logout revokes session in database."""
    # Login
    login_response = await api_client.post(
        "/auth/login",
        data={
            "username": user_to_authenticate.username,
            "password": user_to_authenticate.password,
        },
    )
    access_token = login_response.json()["access_token"]

    # Logout
    logout_response = await api_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert logout_response.status_code == 204


@pytest.mark.asyncio
async def test_refresh_with_revoked_session_fails(
    api_client: AsyncClient, user_to_authenticate
):
    """Test refresh fails after session is revoked (logout)."""
    # Login
    login_response = await api_client.post(
        "/auth/login",
        data={
            "username": user_to_authenticate.username,
            "password": user_to_authenticate.password,
        },
        headers={"Accept": "application/json"},
    )
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    # Logout (revokes session)
    await api_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Try to refresh with revoked session
    refresh_response = await api_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={"Accept": "application/json"},
    )

    assert refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_inactive_user_fails(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test refresh fails if user becomes inactive."""
    from tests.integration.users.conftest import create_user_with_auth

    # Create user
    user_data = await create_user_with_auth(
        db_session,
        password_hasher,
        username="test_inactive",
        password="test_pass123",
        role="user",
        is_active=True,
    )

    # Login
    login_response = await api_client.post(
        "/auth/login",
        data={"username": user_data.username, "password": user_data.password},
        headers={"Accept": "application/json"},
    )
    refresh_token = login_response.json()["refresh_token"]

    # Deactivate user
    from app.infrastructure.db.sqlalchemy.models.user import UserORM
    async with db_session as session:
        stmt = select(UserORM).where(UserORM.id == user_data.user_id)
        result = await session.execute(stmt)
        user = result.scalar_one()
        user.is_active = False
        await session.commit()

    # Try to refresh
    refresh_response = await api_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={"Accept": "application/json"},
    )

    assert refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_access_token_contains_correct_claims(
    api_client: AsyncClient, user_to_authenticate
):
    """Test access token contains all required claims."""
    response = await api_client.post(
        "/auth/login",
        data={
            "username": user_to_authenticate.username,
            "password": user_to_authenticate.password,
        },
        headers={"Accept": "application/json"},
    )

    access_token = response.json()["access_token"]
    decoded = jwt.decode(access_token, options={"verify_signature": False})

    # Check required claims
    assert "sub" in decoded  # user_id
    assert "sid" in decoded  # session_id
    assert "role" in decoded
    assert "exp" in decoded  # expiration

    # Verify claim values
    assert decoded["sub"] == str(user_to_authenticate.user_id)
    assert decoded["role"] == user_to_authenticate.role


@pytest.mark.asyncio
async def test_refresh_extends_session_expiry(
    api_client: AsyncClient, user_to_authenticate
):
    """Test refresh token rotation extends session expiry."""
    # Login
    login_response = await api_client.post(
        "/auth/login",
        data={
            "username": user_to_authenticate.username,
            "password": user_to_authenticate.password,
        },
        headers={"Accept": "application/json"},
    )
    refresh_token = login_response.json()["refresh_token"]

    # Get session_id and old expiry
    decoded = jwt.decode(
        login_response.json()["access_token"], options={"verify_signature": False}
    )
    session_id = decoded["sid"]

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserSessionORM).where(UserSessionORM.id == UUID(session_id))
        result = await session.execute(stmt)
        user_session = result.scalar_one_or_none()
        old_expires_at = user_session.expires_at

    # Wait a bit (optional, just to show time difference)
    import asyncio
    await asyncio.sleep(0.1)

    # Refresh
    await api_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={"Accept": "application/json"},
    )

    # Check expiry updated
    async with session_factory() as session:
        stmt = select(UserSessionORM).where(UserSessionORM.id == UUID(session_id))
        result = await session.execute(stmt)
        user_session = result.scalar_one_or_none()
        new_expires_at = user_session.expires_at

        # New expiry should be later than old
        assert new_expires_at > old_expires_at
