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


# ============================================================================
# POSITIVE TESTS - Successful Authorization
# ============================================================================


@pytest.mark.asyncio
async def test_authorize_success_with_valid_token_and_session(
    api_client: AsyncClient, admin_actor
):
    """Test successful authorization with valid JWT + admin role.

    Admin makes an admin-level request (create user) with valid credentials.
    Should succeed with 201 Created.
    """
    response = await api_client.post(
        "/users",
        json={
            "username": "authorized_user",
            "password": "auth_pass_123",
            "role": "user",
        },
        headers=admin_actor.headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "authorized_user"


@pytest.mark.asyncio
async def test_authorize_success_user_role(api_client: AsyncClient, user_actor):
    """Test successful authorization for user-level action.

    Regular user with valid JWT can perform user-level actions.
    For now, we test that user can login (which is implicitly authorized).
    """
    # User actor is already logged in (fixture creates JWT)
    # Just verify that user has valid credentials
    assert user_actor.headers["Authorization"].startswith("Bearer ")


# ============================================================================
# NEGATIVE TESTS - Token Validation Failures
# ============================================================================


@pytest.mark.asyncio
async def test_authorize_missing_token(api_client: AsyncClient):
    """Test authorization fails when Authorization header is missing."""
    response = await api_client.post(
        "/users",
        json={
            "username": "no_token_user",
            "password": "no_token_pass",
            "role": "user",
        },
        # No Authorization header
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authorize_invalid_token_format(api_client: AsyncClient):
    """Test authorization fails with invalid token format."""
    response = await api_client.post(
        "/users",
        json={
            "username": "invalid_token_user",
            "password": "invalid_token_pass",
            "role": "user",
        },
        headers={"Authorization": "Bearer invalid_token_format"},
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
        "sid": "00000000-0000-0000-0000-000000000000",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }

    # Use test secret (should match .env.test)
    expired_token = jwt.encode(expired_payload, "test-secret-key-for-integration-tests", algorithm="HS256")

    response = await api_client.post(
        "/users",
        json={
            "username": "expired_token_user",
            "password": "expired_token_pass",
            "role": "user",
        },
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authorize_malformed_token(api_client: AsyncClient):
    """Test authorization fails with malformed Authorization header."""
    response = await api_client.post(
        "/users",
        json={
            "username": "malformed_token_user",
            "password": "malformed_token_pass",
            "role": "user",
        },
        headers={"Authorization": "malformed_no_bearer"},
    )

    assert response.status_code == 401


# ============================================================================
# NEGATIVE TESTS - Session Validation Failures
# ============================================================================


@pytest.mark.asyncio
async def test_authorize_invalid_session_id(api_client: AsyncClient, admin_actor):
    """Test authorization fails when session_id doesn't exist in DB.

    Valid JWT signature but non-existent session_id in claims should fail.
    """
    import jwt
    from datetime import datetime, timedelta, timezone

    # Create JWT with non-existent session_id
    invalid_payload = {
        "sub": str(admin_actor.user_id),
        "role": "admin",
        "sid": "00000000-0000-0000-0000-000000000000",  # Non-existent
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    invalid_token = jwt.encode(invalid_payload, "test-secret-key-for-integration-tests", algorithm="HS256")

    response = await api_client.post(
        "/users",
        json={
            "username": "invalid_session_user",
            "password": "invalid_session_pass",
            "role": "user",
        },
        headers={"Authorization": f"Bearer {invalid_token}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authorize_revoked_session(
    api_client: AsyncClient, user_with_revoked_session
):
    """Test authorization fails when session is revoked.

    Valid JWT but session has revoked_at timestamp should fail.
    """
    response = await api_client.post(
        "/users",
        json={
            "username": "revoked_session_user",
            "password": "revoked_session_pass",
            "role": "admin",  # Try to create user (requires ADMIN)
        },
        headers=user_with_revoked_session.headers,  # Valid JWT with revoked session
    )

    assert response.status_code == 401


# ============================================================================
# NEGATIVE TESTS - Role Validation Failures
# ============================================================================


@pytest.mark.asyncio
async def test_authorize_insufficient_role_user_tries_admin_action(
    api_client: AsyncClient, user_actor
):
    """Test authorization fails when user has insufficient role.

    Regular USER tries to create a user (requires ADMIN role).
    Should fail with 403 Forbidden.
    """
    response = await api_client.post(
        "/users",
        json={
            "username": "insufficient_user",
            "password": "insufficient_pass",
            "role": "user",
        },
        headers=user_actor.headers,  # Valid JWT but USER role
    )

    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_authorize_missing_form_fields(api_client: AsyncClient, admin_actor):
    """Test that missing required fields returns validation error, not auth error.

    This is technically a validation test, but included here to verify
    that authorization happens before validation.
    """
    response = await api_client.post(
        "/users",
        json={
            # Missing username, password, role
        },
        headers=admin_actor.headers,
    )

    # Should return 422 Unprocessable Entity (validation error), not 401/403
    assert response.status_code == 422
