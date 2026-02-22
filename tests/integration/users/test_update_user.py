"""Integration tests for update user endpoint."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.integration.users.conftest import create_user_with_auth


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_update_user_username_success(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test admin can update a user's username via PATCH."""
    admin = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="admin_upd", role="admin", with_auth=True,
    )
    target = await create_user_with_auth(
        db_session, password_hasher,
        username="old_name", role="user",
    )

    response = await api_client.patch(
        f"/users/{target.user_id}",
        json={"username": "new_name"},
        headers=admin.headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "new_name"
    assert data["user"]["id"] == str(target.user_id)


@pytest.mark.asyncio
async def test_update_user_role_success(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test admin can change a user's role."""
    admin = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="admin_role", role="admin", with_auth=True,
    )
    target = await create_user_with_auth(
        db_session, password_hasher,
        username="target_role", role="user",
    )

    response = await api_client.patch(
        f"/users/{target.user_id}",
        json={"role": "admin"},
        headers=admin.headers,
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_update_user_response_structure(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test update response has correct structure."""
    admin = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="admin_struct", role="admin", with_auth=True,
    )
    target = await create_user_with_auth(
        db_session, password_hasher,
        username="target_struct", role="user",
    )

    response = await api_client.patch(
        f"/users/{target.user_id}",
        json={"username": "new_struct"},
        headers=admin.headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    user_data = data["user"]
    assert "id" in user_data
    assert "username" in user_data
    assert "role" in user_data
    assert "is_active" in user_data
    assert "password" not in user_data
    assert "password_hash" not in user_data


# ============================================================================
# NEGATIVE TESTS - Not Found
# ============================================================================


@pytest.mark.asyncio
async def test_update_user_not_found(api_client: AsyncClient, admin_actor):
    """Test updating non-existent user returns 404."""
    response = await api_client.patch(
        f"/users/{uuid4()}",
        json={"username": "whatever"},
        headers=admin_actor.headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user_invalid_uuid(api_client: AsyncClient, admin_actor):
    """Test updating user with invalid UUID returns 422."""
    response = await api_client.patch(
        "/users/not-a-uuid",
        json={"username": "whatever"},
        headers=admin_actor.headers,
    )

    assert response.status_code == 422


# ============================================================================
# NEGATIVE TESTS - Conflict
# ============================================================================


@pytest.mark.asyncio
async def test_update_user_duplicate_username(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test updating to existing username returns 409."""
    admin = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="admin_dup", role="admin", with_auth=True,
    )
    user_a = await create_user_with_auth(
        db_session, password_hasher,
        username="user_aaa", role="user",
    )
    await create_user_with_auth(
        db_session, password_hasher,
        username="user_bbb", role="user",
    )

    response = await api_client.patch(
        f"/users/{user_a.user_id}",
        json={"username": "user_bbb"},
        headers=admin.headers,
    )

    assert response.status_code == 409


# ============================================================================
# NEGATIVE TESTS - Authorization
# ============================================================================


@pytest.mark.asyncio
async def test_update_user_forbidden_for_regular_user(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test regular user cannot update users."""
    user = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="regular_usr", role="user", with_auth=True,
    )

    response = await api_client.patch(
        f"/users/{user.user_id}",
        json={"username": "hacked"},
        headers=user.headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_user_without_auth(api_client: AsyncClient):
    """Test updating user without auth returns 401."""
    response = await api_client.patch(
        f"/users/{uuid4()}",
        json={"username": "nope_nope"},
    )

    assert response.status_code == 401
