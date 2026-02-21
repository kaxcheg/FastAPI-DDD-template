"""Integration tests for get user by ID endpoint.

Tests use factory pattern for flexible user creation instead of fixtures.
"""

import pytest
from uuid import uuid4

from httpx import AsyncClient

from tests.integration.users.conftest import create_user_with_auth


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_success_as_user(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test regular user can successfully retrieve a user by ID."""
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        role="user",
        with_auth=True,
    )

    response = await api_client.get(
        f"/users/{actor.user_id}",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert data["user"]["id"] == str(actor.user_id)
    assert data["user"]["username"] == "testuser"
    assert data["user"]["role"] == "user"
    assert data["user"]["is_active"] is True


@pytest.mark.asyncio
async def test_get_user_success_as_admin(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test admin can successfully retrieve a user by ID."""
    admin = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="admin",
        role="admin",
        with_auth=True,
    )

    # Create another user to retrieve
    target = await create_user_with_auth(
        db_session,
        password_hasher,
        username="target_user",
        role="user",
    )

    response = await api_client.get(
        f"/users/{target.user_id}",
        headers=admin.headers,
        cookies=admin.cookies,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == str(target.user_id)
    assert data["user"]["username"] == "target_user"


@pytest.mark.asyncio
async def test_get_user_response_structure(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test that response has correct structure with all required fields."""
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        with_auth=True,
    )

    response = await api_client.get(
        f"/users/{actor.user_id}",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 200
    data = response.json()

    assert "user" in data
    user = data["user"]

    assert "id" in user
    assert "username" in user
    assert "role" in user
    assert "is_active" in user

    assert isinstance(user["id"], str)
    assert isinstance(user["username"], str)
    assert isinstance(user["role"], str)
    assert isinstance(user["is_active"], bool)
    assert user["role"] in ["user", "admin"]


@pytest.mark.asyncio
async def test_get_user_no_password_leak(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test that password hash is not exposed in response."""
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        with_auth=True,
    )

    response = await api_client.get(
        f"/users/{actor.user_id}",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 200
    user = response.json()["user"]

    assert "password" not in user
    assert "password_hash" not in user
    assert "raw_password" not in user
    assert "hashed_password" not in user


@pytest.mark.asyncio
async def test_get_user_returns_inactive_user(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test that inactive user can be retrieved."""
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="active_user",
        role="user",
        with_auth=True,
    )

    inactive = await create_user_with_auth(
        db_session,
        password_hasher,
        username="inactive_user",
        is_active=False,
    )

    response = await api_client.get(
        f"/users/{inactive.user_id}",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "inactive_user"
    assert data["user"]["is_active"] is False


# ============================================================================
# NEGATIVE TESTS - Not Found
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_not_found(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test getting non-existent user returns 404."""
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        with_auth=True,
    )

    non_existent_id = str(uuid4())
    response = await api_client.get(
        f"/users/{non_existent_id}",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_user_invalid_uuid(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test getting user with invalid UUID returns 422."""
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        with_auth=True,
    )

    response = await api_client.get(
        "/users/not-a-valid-uuid",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 422


# ============================================================================
# NEGATIVE TESTS - Authorization
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_without_auth_unauthorized(api_client: AsyncClient):
    """Test getting user without authentication returns 401."""
    response = await api_client.get(f"/users/{uuid4()}")

    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_user_invalid_token(api_client: AsyncClient):
    """Test getting user with invalid JWT token returns 401."""
    response = await api_client.get(
        f"/users/{uuid4()}",
        headers={"Authorization": "Bearer invalid_token_here"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_user_revoked_session(
    api_client: AsyncClient,
    user_with_revoked_session,
):
    """Test getting user with revoked session returns 401."""
    response = await api_client.get(
        f"/users/{uuid4()}",
        headers=user_with_revoked_session.headers,
        cookies=user_with_revoked_session.cookies,
    )

    assert response.status_code == 401
