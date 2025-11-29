"""Integration tests for logout endpoint."""

import pytest
from httpx import AsyncClient
from uuid import UUID
from sqlalchemy import select

from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM


@pytest.mark.asyncio
async def test_logout_success(api_client: AsyncClient, user_actor):
    """Test successful logout returns 204."""
    response = await api_client.post(
        "/auth/logout",
        headers=user_actor.headers,
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_revokes_session_in_db(api_client: AsyncClient, user_actor):
    """Test logout sets revoked_at in database."""
    import jwt
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    # Extract session_id from JWT
    token = user_actor.headers["Authorization"].replace("Bearer ", "")
    decoded = jwt.decode(token, options={"verify_signature": False})
    session_id = decoded["sid"]

    response = await api_client.post(
        "/auth/logout",
        headers=user_actor.headers,
    )

    assert response.status_code == 204

    # Verify session is revoked in DB
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserSessionORM).where(UserSessionORM.id == UUID(session_id))
        result = await session.execute(stmt)
        user_session = result.scalar_one_or_none()

        assert user_session is not None
        assert user_session.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_without_auth_unauthorized(api_client: AsyncClient):
    """Test logout without authentication returns 401."""
    response = await api_client.post("/auth/logout")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalid_token(api_client: AsyncClient):
    """Test logout with invalid token returns 401."""
    response = await api_client.post(
        "/auth/logout",
        headers={"Authorization": "Bearer invalid_token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_second_time_same_session_is_idempotent(
    api_client: AsyncClient, user_actor
):
    """Test logout is idempotent - second logout still returns 204.

    Middleware only validates JWT, not DB session state.
    So second logout passes middleware but revoke() is a no-op.
    """
    # First logout
    response1 = await api_client.post(
        "/auth/logout",
        headers=user_actor.headers,
    )
    assert response1.status_code == 204

    # Second logout - idempotent, still 204
    response2 = await api_client.post(
        "/auth/logout",
        headers=user_actor.headers,
    )
    assert response2.status_code == 204


@pytest.mark.asyncio
async def test_logout_then_access_protected_endpoint(api_client: AsyncClient, user_actor):
    """Test accessing protected endpoint after logout returns 401."""
    # Logout
    response = await api_client.post(
        "/auth/logout",
        headers=user_actor.headers,
    )
    assert response.status_code == 204

    # Try to access protected endpoint
    response = await api_client.get(
        "/users",
        headers=user_actor.headers,
    )
    assert response.status_code == 401
