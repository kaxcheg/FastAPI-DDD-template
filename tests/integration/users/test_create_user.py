"""Integration tests for create user use case.

Tests cover positive and negative scenarios for user creation,
similar to tests/unit/application/test_create_user.py but at integration level.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.infrastructure.db.sqlalchemy.models.user import UserORM


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_success_as_admin(api_client: AsyncClient, admin_actor):
    """Test admin can successfully create a new user."""
    response = await api_client.post(
        "/users",
        json={
            "username": "new_user",
            "password": "secure_pass_123",
            "role": "user",
        },
        headers=admin_actor.headers,
        cookies=admin_actor.cookies,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "new_user"
    assert data["role"] == "user"
    assert "id" in data

    # Verify user exists in DB
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserORM).where(UserORM.username == "new_user")
        result = await session.execute(stmt)
        new_user = result.scalar_one_or_none()

        assert new_user is not None
        assert new_user.username == "new_user"
        assert new_user.role == "user"
        assert new_user.is_active is True


@pytest.mark.asyncio
async def test_create_admin_user_success_as_admin(api_client: AsyncClient, admin_actor):
    """Test admin can create another admin user."""
    response = await api_client.post(
        "/users",
        json={
            "username": "new_admin",
            "password": "admin_pass_123",
            "role": "admin",
        },
        headers=admin_actor.headers,
        cookies=admin_actor.cookies,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "new_admin"
    assert data["role"] == "admin"

    # Verify in DB
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserORM).where(UserORM.username == "new_admin")
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
    api_client: AsyncClient, admin_actor
):
    """Test creating user with existing username returns conflict."""
    response = await api_client.post(
        "/users",
        json={
            "username": admin_actor.username,  # Already exists
            "password": "password123",
            "role": "user",
        },
        headers=admin_actor.headers,
        cookies=admin_actor.cookies,
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


# ============================================================================
# NEGATIVE TESTS - Validation Errors
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_invalid_username(api_client: AsyncClient, admin_actor):
    """Test creating user with invalid username fails."""
    response = await api_client.post(
        "/users",
        json={
            "username": "",  # Empty username
            "password": "password123",
            "role": "user",
        },
        headers=admin_actor.headers,
        cookies=admin_actor.cookies,
    )

    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_create_user_invalid_password(api_client: AsyncClient, admin_actor):
    """Test creating user with invalid password fails."""
    response = await api_client.post(
        "/users",
        json={
            "username": "validuser",
            "password": "",  # Empty password
            "role": "user",
        },
        headers=admin_actor.headers,
        cookies=admin_actor.cookies,
    )

    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_create_user_invalid_role(api_client: AsyncClient, admin_actor):
    """Test creating user with invalid role fails."""
    response = await api_client.post(
        "/users",
        json={
            "username": "validuser",
            "password": "password123",
            "role": "INVALID_ROLE",
        },
        headers=admin_actor.headers,
        cookies=admin_actor.cookies,
    )

    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_create_user_missing_required_fields(api_client: AsyncClient, admin_actor):
    """Test creating user with missing fields fails."""
    response = await api_client.post(
        "/users",
        json={
            # Missing username, password, role
        },
        headers=admin_actor.headers,
        cookies=admin_actor.cookies,
    )

    assert response.status_code == 422  # FastAPI validation error


# ============================================================================
# SECURITY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_password_is_hashed(api_client: AsyncClient, admin_actor):
    """Test that user password is properly hashed in database."""
    plain_password = "secure_pass_123"  # Max 20 chars

    response = await api_client.post(
        "/users",
        json={
            "username": "hashtest",
            "password": plain_password,
            "role": "user",
        },
        headers=admin_actor.headers,
        cookies=admin_actor.cookies,
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
    api_client: AsyncClient, user_actor
):
    """Test regular user cannot create users (requires ADMIN role)."""
    response = await api_client.post(
        "/users",
        json={
            "username": "forbidden_user",
            "password": "forbidden_pass_123",
            "role": "user",
        },
        headers=user_actor.headers,
        cookies=user_actor.cookies,
    )

    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_user_without_auth_unauthorized(api_client: AsyncClient):
    """Test creating user without authentication returns 401."""
    response = await api_client.post(
        "/users",
        json={
            "username": "unauth_user",
            "password": "unauth_pass_123",
            "role": "user",
        },
    )

    assert response.status_code == 401
