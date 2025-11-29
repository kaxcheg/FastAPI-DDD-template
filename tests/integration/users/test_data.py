"""Test data for integration tests.

This module contains centralized test data definitions to avoid hardcoding
values in test functions. Similar to tests/adapters.py:TestUser for unit tests.
"""

from dataclasses import dataclass


@dataclass
class IntegrationTestUser:
    """Test user data structure for integration tests."""

    username: str
    raw_password: str
    role: str
    is_active: bool = True


class IntegrationTestUsers:
    """Centralized test user data.

    All test users are defined here to avoid hardcoding credentials
    in test functions and fixtures.

    Tables are reset (DROP/CREATE) after each test, so username conflicts
    are not an issue. All fixtures can use the same base users.
    """

    # Base users for most tests
    REGULAR_USER = IntegrationTestUser(
        username="test_user",
        raw_password="user_password",
        role="user",
        is_active=True,
    )

    ADMIN_USER = IntegrationTestUser(
        username="test_admin",
        raw_password="admin_password",
        role="admin",
        is_active=True,
    )

    INACTIVE_USER = IntegrationTestUser(
        username="inactive",
        raw_password="inactive_password",
        role="user",
        is_active=False,
    )

    # Users for CRUD operations in create_user tests
    USER_TO_CREATE = IntegrationTestUser(
        username="new_user",
        raw_password="secure_pass_123",
        role="user",
        is_active=True,
    )

    ADMIN_TO_CREATE = IntegrationTestUser(
        username="new_admin",
        raw_password="admin_pass_123",
        role="admin",
        is_active=True,
    )
