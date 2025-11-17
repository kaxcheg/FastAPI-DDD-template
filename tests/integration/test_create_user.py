"""Integration tests for create user use case.

Tests cover positive and negative scenarios for user creation,
similar to tests/unit/application/test_create_user.py but at integration level.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.infrastructure.db.sqlalchemy.models.user import UserORM
from tests.integration.test_data import IntegrationTestUsers


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_success_as_admin(api_client: AsyncClient, admin_actor: dict):
    """Test admin can successfully create a new user."""
    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
        headers=admin_actor["headers"],
        cookies=admin_actor["cookies"],
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == user_data.username
    assert data["role"] == user_data.role
    assert "id" in data

    # Verify user exists in DB
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserORM).where(UserORM.username == user_data.username)
        result = await session.execute(stmt)
        new_user = result.scalar_one_or_none()

        assert new_user is not None
        assert new_user.username == user_data.username
        assert new_user.role == user_data.role
        assert new_user.is_active is True


@pytest.mark.asyncio
async def test_create_admin_user_success_as_admin(api_client: AsyncClient, admin_actor: dict):
    """Test admin can create another admin user."""
    user_data = IntegrationTestUsers.ADMIN_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
        headers=admin_actor["headers"],
        cookies=admin_actor["cookies"],
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == user_data.username
    assert data["role"] == "admin"

    # Verify in DB
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserORM).where(UserORM.username == user_data.username)
        result = await session.execute(stmt)
        new_admin = result.scalar_one_or_none()

        assert new_admin is not None
        assert new_admin.role == "admin"
        assert new_admin.is_active is True


# ============================================================================
# NEGATIVE TESTS - Conflict
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_duplicate_username_conflict(
    api_client: AsyncClient, admin_actor: dict, user_to_authenticate: UserORM
):
    """Test creating user with existing username returns conflict."""
    response = await api_client.post(
        "/users",
        json={
            "username": user_to_authenticate.username,  # Already exists
            "password": "password123",
            "role": "user",
        },
        headers=admin_actor["headers"],
        cookies=admin_actor["cookies"],
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


# ============================================================================
# NEGATIVE TESTS - Validation Errors
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_invalid_username(api_client: AsyncClient, admin_actor: dict):
    """Test creating user with invalid username fails."""
    response = await api_client.post(
        "/users",
        json={
            "username": "",  # Empty username
            "password": "password123",
            "role": "user",
        },
        headers=admin_actor["headers"],
        cookies=admin_actor["cookies"],
    )

    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_create_user_invalid_password(api_client: AsyncClient, admin_actor: dict):
    """Test creating user with invalid password fails."""
    response = await api_client.post(
        "/users",
        json={
            "username": "validuser",
            "password": "",  # Empty password
            "role": "user",
        },
        headers=admin_actor["headers"],
        cookies=admin_actor["cookies"],
    )

    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_create_user_invalid_role(api_client: AsyncClient, admin_actor: dict):
    """Test creating user with invalid role fails."""
    response = await api_client.post(
        "/users",
        json={
            "username": "validuser",
            "password": "password123",
            "role": "INVALID_ROLE",
        },
        headers=admin_actor["headers"],
        cookies=admin_actor["cookies"],
    )

    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_create_user_missing_required_fields(api_client: AsyncClient, admin_actor: dict):
    """Test creating user with missing fields fails."""
    response = await api_client.post(
        "/users",
        json={
            # Missing username, password, role
        },
        headers=admin_actor["headers"],
        cookies=admin_actor["cookies"],
    )

    assert response.status_code == 422  # FastAPI validation error


# ============================================================================
# SECURITY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_password_is_hashed(api_client: AsyncClient, admin_actor: dict):
    """Test that user password is properly hashed in database."""
    plain_password = "secure_pass_123"  # Max 20 chars

    response = await api_client.post(
        "/users",
        json={
            "username": "hashtest",
            "password": plain_password,
            "role": "user",
        },
        headers=admin_actor["headers"],
        cookies=admin_actor["cookies"],
    )

    assert response.status_code == 201

    # Verify password is hashed (not stored as plain text)
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserORM).where(UserORM.username == "hashtest")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.password_hash != plain_password.encode()
        # Bcrypt hashes start with $2b$
        assert user.password_hash.startswith(b"$2b$")


# ============================================================================
# AUTHORIZATION TESTS (included here as they're specific to create_user endpoint)
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_as_regular_user_forbidden(
    api_client: AsyncClient, user_actor: dict
):
    """Test regular user cannot create users (requires ADMIN role)."""
    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
        headers=user_actor["headers"],
        cookies=user_actor["cookies"],
    )

    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_user_without_auth_unauthorized(api_client: AsyncClient):
    """Test creating user without authentication returns 401."""
    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
    )

    assert response.status_code == 401
