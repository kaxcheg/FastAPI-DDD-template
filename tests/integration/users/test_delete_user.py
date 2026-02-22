"""Integration tests for delete (soft-delete) user endpoint."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.infrastructure.db.sqlalchemy.models.user import UserORM
from tests.integration.users.conftest import create_user_with_auth


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_delete_user_success(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test admin can soft-delete a user via DELETE."""
    admin = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="admin_del", role="admin", with_auth=True,
    )
    target = await create_user_with_auth(
        db_session, password_hasher,
        username="target_del", role="user",
    )

    response = await api_client.delete(
        f"/users/{target.user_id}",
        headers=admin.headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == str(target.user_id)
    assert data["user"]["is_active"] is False


@pytest.mark.asyncio
async def test_delete_user_persisted_in_db(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test soft-deleted user is deactivated in the database."""
    admin = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="admin_dbdel", role="admin", with_auth=True,
    )
    target = await create_user_with_auth(
        db_session, password_hasher,
        username="target_dbdel", role="user",
    )

    response = await api_client.delete(
        f"/users/{target.user_id}",
        headers=admin.headers,
    )
    assert response.status_code == 200

    # Verify in DB
    from app.infrastructure.db.sqlalchemy.setup import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(UserORM).where(UserORM.id == target.user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.is_active is False


# ============================================================================
# NEGATIVE TESTS - Self-Deletion
# ============================================================================


@pytest.mark.asyncio
async def test_delete_user_self_deletion_forbidden(
    api_client: AsyncClient, admin_actor
):
    """Test admin cannot delete themselves."""
    response = await api_client.delete(
        f"/users/{admin_actor.user_id}",
        headers=admin_actor.headers,
    )

    assert response.status_code == 400
    assert "cannot delete themselves" in response.json()["detail"].lower()


# ============================================================================
# NEGATIVE TESTS - Not Found
# ============================================================================


@pytest.mark.asyncio
async def test_delete_user_not_found(api_client: AsyncClient, admin_actor):
    """Test deleting non-existent user returns 404."""
    response = await api_client.delete(
        f"/users/{uuid4()}",
        headers=admin_actor.headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_invalid_uuid(api_client: AsyncClient, admin_actor):
    """Test deleting user with invalid UUID returns 422."""
    response = await api_client.delete(
        "/users/not-a-uuid",
        headers=admin_actor.headers,
    )

    assert response.status_code == 422


# ============================================================================
# NEGATIVE TESTS - Already Inactive
# ============================================================================


@pytest.mark.asyncio
async def test_delete_user_already_inactive(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test deleting already inactive user returns 422."""
    admin = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="admin_inact", role="admin", with_auth=True,
    )
    target = await create_user_with_auth(
        db_session, password_hasher,
        username="inactive_usr", role="user", is_active=False,
    )

    response = await api_client.delete(
        f"/users/{target.user_id}",
        headers=admin.headers,
    )

    assert response.status_code == 422


# ============================================================================
# NEGATIVE TESTS - Authorization
# ============================================================================


@pytest.mark.asyncio
async def test_delete_user_forbidden_for_regular_user(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test regular user cannot delete users."""
    user = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="regular_del", role="user", with_auth=True,
    )

    response = await api_client.delete(
        f"/users/{user.user_id}",
        headers=user.headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_without_auth(api_client: AsyncClient):
    """Test deleting user without auth returns 401."""
    response = await api_client.delete(
        f"/users/{uuid4()}",
    )

    assert response.status_code == 401
