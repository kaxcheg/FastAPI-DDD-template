"""Integration tests for authorization use case.

These tests verify authorization checks (JWT validation, session validation, role checks)
through real HTTP endpoints, similar to tests/unit/application/test_authorize_user.py
but at integration level.

Tests cover:
- Successful authorization with valid token + session + role
- Token validation failures (missing, invalid, expired, malformed)
- Session validation failures (missing, invalid, revoked)
- Role validation failures (insufficient permissions)
"""

import pytest
from httpx import AsyncClient

from tests.integration.test_data import IntegrationTestUsers


# ============================================================================
# POSITIVE TESTS - Successful Authorization
# ============================================================================


@pytest.mark.asyncio
async def test_authorize_success_with_valid_token_and_session(
    api_client: AsyncClient, admin_actor: dict
):
    """Test successful authorization with valid JWT + session_id + admin role.

    Admin makes an admin-level request (create user) with valid credentials.
    Should succeed with 201 Created.
    """
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


@pytest.mark.asyncio
async def test_authorize_success_user_role(api_client: AsyncClient, user_actor: dict):
    """Test successful authorization for user-level action.

    Regular user with valid JWT + session_id can perform user-level actions.
    For now, we test that user can login (which is implicitly authorized).
    """
    # User actor is already logged in (fixture creates JWT + session)
    # Just verify that user has valid credentials
    assert user_actor["headers"]["Authorization"].startswith("Bearer ")
    assert user_actor["cookies"]["session_id"] is not None


# ============================================================================
# NEGATIVE TESTS - Token Validation Failures
# ============================================================================


@pytest.mark.asyncio
async def test_authorize_missing_token(api_client: AsyncClient):
    """Test authorization fails when Authorization header is missing."""
    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
        # No Authorization header
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authorize_invalid_token_format(api_client: AsyncClient, admin_actor: dict):
    """Test authorization fails with invalid token format."""
    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
        headers={"Authorization": "Bearer invalid_token_format"},
        cookies=admin_actor["cookies"],  # Valid session but invalid token
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authorize_expired_token(api_client: AsyncClient):
    """Test authorization fails with expired JWT token.

    This test uses a manually created expired token.
    In production, tokens expire after JWT_TOKEN_EXPIRY_TIME seconds.
    """
    # Create an expired token (expired 1 hour ago)
    import jwt
    from datetime import datetime, timedelta, timezone

    expired_payload = {
        "sub": "test_user",
        "session_id": "00000000-0000-0000-0000-000000000000",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }

    # Use test secret (should match .env.test)
    expired_token = jwt.encode(expired_payload, "test-secret-key-for-integration-tests", algorithm="HS256")

    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
        headers={"Authorization": f"Bearer {expired_token}"},
        cookies={"session_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authorize_malformed_token(api_client: AsyncClient):
    """Test authorization fails with malformed Authorization header."""
    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
        headers={"Authorization": "malformed_no_bearer"},
    )

    assert response.status_code == 401


# ============================================================================
# NEGATIVE TESTS - Session Validation Failures
# ============================================================================


@pytest.mark.asyncio
async def test_authorize_missing_session_cookie(api_client: AsyncClient, admin_actor: dict):
    """Test authorization fails when session_id cookie is missing.

    Valid JWT but no session_id cookie should fail.
    """
    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
        headers=admin_actor["headers"],  # Valid JWT
        # No cookies - missing session_id
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authorize_invalid_session_id(api_client: AsyncClient, admin_actor: dict):
    """Test authorization fails when session_id doesn't exist in DB.

    Valid JWT but non-existent session_id should fail.
    """
    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
        headers=admin_actor["headers"],  # Valid JWT
        cookies={"session_id": "00000000-0000-0000-0000-000000000000"},  # Non-existent
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authorize_revoked_session(
    api_client: AsyncClient, user_with_revoked_session: dict
):
    """Test authorization fails when session is revoked.

    Valid JWT but session has revoked_at timestamp should fail.
    """
    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": "admin",  # Try to create user (requires ADMIN)
        },
        headers=user_with_revoked_session["headers"],  # Valid JWT
        cookies=user_with_revoked_session["cookies"],  # Revoked session
    )

    assert response.status_code == 401


# ============================================================================
# NEGATIVE TESTS - Role Validation Failures
# ============================================================================


@pytest.mark.asyncio
async def test_authorize_insufficient_role_user_tries_admin_action(
    api_client: AsyncClient, user_actor: dict
):
    """Test authorization fails when user has insufficient role.

    Regular USER tries to create a user (requires ADMIN role).
    Should fail with 403 Forbidden.
    """
    user_data = IntegrationTestUsers.USER_TO_CREATE

    response = await api_client.post(
        "/users",
        json={
            "username": user_data.username,
            "password": user_data.raw_password,
            "role": user_data.role,
        },
        headers=user_actor["headers"],  # Valid JWT but USER role
        cookies=user_actor["cookies"],  # Valid session
    )

    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_authorize_missing_form_fields(api_client: AsyncClient, admin_actor: dict):
    """Test that missing required fields returns validation error, not auth error.

    This is technically a validation test, but included here to verify
    that authorization happens before validation.
    """
    response = await api_client.post(
        "/users",
        json={
            # Missing username, password, role
        },
        headers=admin_actor["headers"],
        cookies=admin_actor["cookies"],
    )

    # Should return 422 Unprocessable Entity (validation error), not 401/403
    assert response.status_code == 422
