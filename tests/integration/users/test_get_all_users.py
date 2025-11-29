"""Integration tests for get all users use case.

Tests use factory pattern for flexible user creation instead of fixtures.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.infrastructure.db.sqlalchemy.models.user import UserORM
from tests.integration.users.conftest import create_user_with_auth


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_users_success_as_user(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test regular user can successfully retrieve all users."""
    # Create authenticated user
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        role="user",
        with_auth=True,
    )

    response = await api_client.get(
        "/users",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert isinstance(data["users"], list)
    assert len(data["users"]) > 0


@pytest.mark.asyncio
async def test_get_all_users_success_as_admin(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test admin can successfully retrieve all users."""
    # Create authenticated admin
    admin = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="admin",
        role="admin",
        with_auth=True,
    )

    response = await api_client.get(
        "/users",
        headers=admin.headers,
        cookies=admin.cookies,
    )

    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert isinstance(data["users"], list)
    assert len(data["users"]) > 0


@pytest.mark.asyncio
async def test_get_all_users_returns_all_users(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test that all users from database are returned."""
    # Create authenticated user
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        role="user",
        with_auth=True,
    )

    # Create additional users (no auth needed)
    user1 = await create_user_with_auth(
        db_session, password_hasher, username="user1", role="user"
    )
    user2 = await create_user_with_auth(
        db_session, password_hasher, username="admin1", role="admin"
    )

    response = await api_client.get(
        "/users",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all users are present
    usernames = {user["username"] for user in data["users"]}
    assert "testuser" in usernames
    assert user1.username in usernames
    assert user2.username in usernames

    # Verify count matches database
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserORM)
        result = await session.execute(stmt)
        db_users = result.scalars().all()

        assert len(data["users"]) == len(db_users)


@pytest.mark.asyncio
async def test_get_all_users_includes_inactive_users(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test that inactive users are also included in the response."""
    # Create authenticated user
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        role="user",
        with_auth=True,
    )

    # Create inactive user
    inactive = await create_user_with_auth(
        db_session,
        password_hasher,
        username="inactive_user",
        is_active=False,
    )

    response = await api_client.get(
        "/users",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 200
    data = response.json()

    # Find the inactive user in response
    inactive_in_response = None
    for user in data["users"]:
        if user["username"] == inactive.username:
            inactive_in_response = user
            break

    assert inactive_in_response is not None
    assert inactive_in_response["is_active"] is False


# ============================================================================
# NEGATIVE TESTS - Authorization
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_users_without_auth_unauthorized(api_client: AsyncClient):
    """Test getting users without authentication returns 401."""
    response = await api_client.get("/users")

    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_all_users_invalid_token(api_client: AsyncClient):
    """Test getting users with invalid JWT token returns 401."""
    response = await api_client.get(
        "/users",
        headers={"Authorization": "Bearer invalid_token_here"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_all_users_revoked_session(
    api_client: AsyncClient,
    user_with_revoked_session,
):
    """Test getting users with revoked session returns 401."""
    response = await api_client.get(
        "/users",
        headers=user_with_revoked_session.headers,
        cookies=user_with_revoked_session.cookies,
    )

    assert response.status_code == 401


# ============================================================================
# DATA VERIFICATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_users_response_structure(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test that response has correct structure with all required fields."""
    # Create authenticated user
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        with_auth=True,
    )

    response = await api_client.get(
        "/users",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify top-level structure
    assert "users" in data
    assert isinstance(data["users"], list)

    # Verify each user has correct fields
    for user in data["users"]:
        assert "id" in user
        assert "username" in user
        assert "role" in user
        assert "is_active" in user

        # Verify field types
        assert isinstance(user["id"], str)
        assert isinstance(user["username"], str)
        assert isinstance(user["role"], str)
        assert isinstance(user["is_active"], bool)

        # Verify role is valid
        assert user["role"] in ["user", "admin"]


@pytest.mark.asyncio
async def test_get_all_users_no_password_leak(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test that password hashes are not exposed in response."""
    # Create authenticated user
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        with_auth=True,
    )

    response = await api_client.get(
        "/users",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify no password fields are present
    for user in data["users"]:
        assert "password" not in user
        assert "password_hash" not in user
        assert "raw_password" not in user
        assert "hashed_password" not in user


@pytest.mark.asyncio
async def test_get_all_users_includes_all_roles(
    api_client: AsyncClient,
    db_session,
    password_hasher,
):
    """Test that users with different roles are all included."""
    # Create authenticated user
    actor = await create_user_with_auth(
        db_session,
        password_hasher,
        api_client,
        username="testuser",
        role="user",
        with_auth=True,
    )

    # Create users with different roles
    await create_user_with_auth(
        db_session, password_hasher, username="user1", role="user"
    )
    await create_user_with_auth(
        db_session, password_hasher, username="admin1", role="admin"
    )

    response = await api_client.get(
        "/users",
        headers=actor.headers,
        cookies=actor.cookies,
    )

    assert response.status_code == 200
    data = response.json()

    roles_in_response = {user["role"] for user in data["users"]}

    # Verify both user and admin roles are present
    assert "user" in roles_in_response
    assert "admin" in roles_in_response
