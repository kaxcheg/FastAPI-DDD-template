import pytest

from app.domain.value_objects import UserId, UserRole
from app.domain.value_objects.constants import HASH_LEN

from app.application.use_cases.authenticate_user import AuthenticateUserUseCase

from tests.adapters import (
    TestUser, 
    FakeUoW, 
    FakePasswordVerifier, 
    FakePasswordHasher,
    FakeIdGenerator
)


@pytest.fixture
def initial_users():
    """Fixture with initial test users"""
    return [
        TestUser(
            id=str(UserId.new()),
            username="testuser",
            raw_password="testpass123",
            password_hash="a" * HASH_LEN,
            role=UserRole.USER
        ),
        TestUser(
            id=str(UserId.new()),
            username="admin",
            raw_password="adminpass456",
            password_hash="b" * HASH_LEN,
            role=UserRole.ADMIN
        )
    ]


@pytest.fixture
def uow_factory(initial_users):
    """UoW factory fixture."""

    uow = FakeUoW(initial_users)
    def factory():
        return uow
    return factory


@pytest.fixture
def password_verifier(initial_users):
    """Password verifier fixture."""
    return FakePasswordVerifier(initial_users)

@pytest.fixture
def authenticate_use_case(uow_factory, password_verifier):
    """AuthenticateUserUseCase fixture."""
    return AuthenticateUserUseCase(uow_factory, password_verifier)


@pytest.fixture(scope="session")
def password_hasher():
    """Password hasher fixture."""
    return FakePasswordHasher()


@pytest.fixture(scope="session")
def id_generator():
    """ID generator fixture."""
    return FakeIdGenerator()

# @pytest.fixture(scope="session")
# def successful_auth_service():
#     return FakeAuthService(is_user_found=True, is_role_ensured=True)
