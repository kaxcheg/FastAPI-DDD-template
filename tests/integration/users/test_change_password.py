"""Integration tests for change password endpoint."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.integration.users.conftest import create_user_with_auth


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_change_password_success(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test admin can change a user's password via PATCH."""
    admin = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="admin_chpw", role="admin", with_auth=True,
    )
    target = await create_user_with_auth(
        db_session, password_hasher,
        username="target_chpw", role="user",
    )

    response = await api_client.patch(
        f"/users/{target.user_id}/password",
        json={"new_password": "newpass123"},
        headers=admin.headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == str(target.user_id)
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_change_password_user_can_login_with_new(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test user can login with the new password after change."""
    admin = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="admin_login", role="admin", with_auth=True,
    )
    target = await create_user_with_auth(
        db_session, password_hasher,
        username="target_login", password="old_password", role="user",
    )

    # Change password
    response = await api_client.patch(
        f"/users/{target.user_id}/password",
        json={"new_password": "new_password"},
        headers=admin.headers,
    )
    assert response.status_code == 200

    # Login with new password should succeed
    login_response = await api_client.post(
        "/auth/login",
        data={"username": "target_login", "password": "new_password"},
    )
    assert login_response.status_code == 200

    # Login with old password should fail
    old_login = await api_client.post(
        "/auth/login",
        data={"username": "target_login", "password": "old_password"},
    )
    assert old_login.status_code == 401


# ============================================================================
# NEGATIVE TESTS - Not Found
# ============================================================================


@pytest.mark.asyncio
async def test_change_password_not_found(api_client: AsyncClient, admin_actor):
    """Test changing password for non-existent user returns 404."""
    response = await api_client.patch(
        f"/users/{uuid4()}/password",
        json={"new_password": "newpass123"},
        headers=admin_actor.headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_change_password_invalid_uuid(api_client: AsyncClient, admin_actor):
    """Test changing password with invalid UUID returns 422."""
    response = await api_client.patch(
        "/users/not-a-uuid/password",
        json={"new_password": "newpass123"},
        headers=admin_actor.headers,
    )

    assert response.status_code == 422


# ============================================================================
# NEGATIVE TESTS - Validation
# ============================================================================


@pytest.mark.asyncio
async def test_change_password_too_short(api_client: AsyncClient, admin_actor):
    """Test password that is too short returns 422."""
    response = await api_client.patch(
        f"/users/{uuid4()}/password",
        json={"new_password": "ab"},
        headers=admin_actor.headers,
    )

    assert response.status_code == 422


# ============================================================================
# NEGATIVE TESTS - Authorization
# ============================================================================


@pytest.mark.asyncio
async def test_change_password_forbidden_for_regular_user(
    api_client: AsyncClient, db_session, password_hasher
):
    """Test regular user cannot change passwords."""
    user = await create_user_with_auth(
        db_session, password_hasher, api_client,
        username="regular_chpw", role="user", with_auth=True,
    )

    response = await api_client.patch(
        f"/users/{user.user_id}/password",
        json={"new_password": "newpass123"},
        headers=user.headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_change_password_without_auth(api_client: AsyncClient):
    """Test changing password without auth returns 401."""
    response = await api_client.patch(
        f"/users/{uuid4()}/password",
        json={"new_password": "newpass123"},
    )

    assert response.status_code == 401
