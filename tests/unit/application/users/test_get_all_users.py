"""Unit tests for GetAllUsers use case.

Tests cover positive and negative scenarios for retrieving all users,
following patterns from tests/unit/application/test_create_user.py.
"""

import pytest


from app.application.dto import GetAllUsersInputDTO, GetAllUsersOutputDTO
from app.application.ports import State
from app.application.use_cases.get_all_users import GetAllUsersUseCase

from tests.adapters import FakeAuthService, FakeGetAllUsersPresenter


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_users_success(
    uow_factory,
    initial_users,
):
    """Test successful retrieval of all users."""

    auth_service = FakeAuthService(is_user_found=True)

    use_case = GetAllUsersUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = GetAllUsersInputDTO()
    presenter = FakeGetAllUsersPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, GetAllUsersOutputDTO)
    assert len(presenter.response.users) == len(initial_users)

    # Verify all initial users are returned
    returned_usernames = {user.username for user in presenter.response.users}
    expected_usernames = {user.username for user in initial_users}
    assert returned_usernames == expected_usernames


@pytest.mark.asyncio
async def test_get_all_users_empty_repository():
    """Test get all users returns empty list when no users exist."""

    # Create UoW factory with empty user list
    def empty_uow_factory():
        from tests.adapters import FakeUoW

        return FakeUoW(initial_users=[])

    auth_service = FakeAuthService(is_user_found=True)

    use_case = GetAllUsersUseCase(
        auth_service=auth_service,
        uow_factory=empty_uow_factory,
    )

    dto = GetAllUsersInputDTO()
    presenter = FakeGetAllUsersPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, GetAllUsersOutputDTO)
    assert len(presenter.response.users) == 0
    assert presenter.response.users == []


@pytest.mark.asyncio
async def test_get_all_users_multiple_users(
    uow_factory,
    initial_users,
):
    """Test get all users returns correct data for multiple users."""

    auth_service = FakeAuthService(is_user_found=True)

    use_case = GetAllUsersUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = GetAllUsersInputDTO()
    presenter = FakeGetAllUsersPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, GetAllUsersOutputDTO)

    # Verify each returned user has correct structure
    for user_dto in presenter.response.users:
        assert hasattr(user_dto, "id")
        assert hasattr(user_dto, "username")
        assert hasattr(user_dto, "role")
        assert hasattr(user_dto, "is_active")
        assert isinstance(user_dto.id, str)
        assert isinstance(user_dto.username, str)
        assert isinstance(user_dto.role, str)
        assert isinstance(user_dto.is_active, bool)


@pytest.mark.asyncio
async def test_get_all_users_no_password_leak(
    uow_factory,
    initial_users,
):
    """Test that password hashes are not leaked in response DTOs."""

    auth_service = FakeAuthService(is_user_found=True)

    use_case = GetAllUsersUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = GetAllUsersInputDTO()
    presenter = FakeGetAllUsersPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, GetAllUsersOutputDTO)

    # Verify no password-related fields in DTOs
    for user_dto in presenter.response.users:
        assert not hasattr(user_dto, "password")
        assert not hasattr(user_dto, "password_hash")
        assert not hasattr(user_dto, "raw_password")

