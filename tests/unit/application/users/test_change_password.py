"""Unit tests for ChangePassword use case."""

import pytest

from app.application.dto import ChangePasswordInputDTO, ChangePasswordOutputDTO
from app.application.ports import State
from app.application.use_cases.change_password import ChangePasswordUseCase
from app.domain.value_objects import UserId, UserRole

from tests.adapters import FakeAuthService, FakeChangePasswordPresenter, FakeUoW


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_change_password_success(uow_factory, initial_users, password_hasher):
    """Test admin can change a user's password."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = ChangePasswordUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=password_hasher,
    )

    target = initial_users[0]
    dto = ChangePasswordInputDTO(user_id=target.id, new_password="newpass123")
    presenter = FakeChangePasswordPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, ChangePasswordOutputDTO)
    assert presenter.response.user.id == target.id


# ============================================================================
# NEGATIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_change_password_not_found(uow_factory, password_hasher):
    """Test changing password for non-existent user returns NOT_FOUND."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = ChangePasswordUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=password_hasher,
    )

    dto = ChangePasswordInputDTO(user_id=str(UserId.new()), new_password="newpass123")
    presenter = FakeChangePasswordPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.NOT_FOUND
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_change_password_invalid_uuid(uow_factory, password_hasher):
    """Test invalid UUID returns DOMAIN_ERROR."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = ChangePasswordUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=password_hasher,
    )

    dto = ChangePasswordInputDTO(user_id="not-a-uuid", new_password="newpass123")
    presenter = FakeChangePasswordPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.DOMAIN_ERROR
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_change_password_too_short(uow_factory, initial_users, password_hasher):
    """Test password that is too short returns DOMAIN_ERROR."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = ChangePasswordUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=password_hasher,
    )

    target = initial_users[0]
    dto = ChangePasswordInputDTO(user_id=target.id, new_password="ab")
    presenter = FakeChangePasswordPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.DOMAIN_ERROR
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_change_password_unauthorized():
    """Test unauthenticated request returns UNAUTHORIZED."""
    auth_service = FakeAuthService(is_user_found=False)

    def uow_factory():
        return FakeUoW(initial_users=[])

    use_case = ChangePasswordUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=__import__("tests.adapters", fromlist=["FakePasswordHasher"]).FakePasswordHasher(),
    )

    dto = ChangePasswordInputDTO(user_id=str(UserId.new()), new_password="newpass123")
    presenter = FakeChangePasswordPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.UNAUTHORIZED
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_change_password_forbidden_for_regular_user():
    """Test regular user cannot change passwords."""
    auth_service = FakeAuthService(is_user_found=True, user_role=UserRole.USER)

    def uow_factory():
        return FakeUoW(initial_users=[])

    use_case = ChangePasswordUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
        hasher=__import__("tests.adapters", fromlist=["FakePasswordHasher"]).FakePasswordHasher(),
    )

    dto = ChangePasswordInputDTO(user_id=str(UserId.new()), new_password="newpass123")
    presenter = FakeChangePasswordPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.FORBIDDEN
    assert isinstance(presenter.response, str)
