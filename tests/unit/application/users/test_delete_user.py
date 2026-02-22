"""Unit tests for DeleteUser use case."""

import pytest

from app.application.dto import DeleteUserInputDTO, DeleteUserOutputDTO
from app.application.ports import State
from app.application.use_cases.delete_user import DeleteUserUseCase
from app.domain.value_objects import UserId, UserRole

from tests.adapters import FakeAuthService, FakeDeleteUserPresenter, FakeUoW


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_delete_user_success(uow_factory, initial_users):
    """Test admin can soft-delete (deactivate) a user."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = DeleteUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target = initial_users[0]
    dto = DeleteUserInputDTO(user_id=target.id)
    presenter = FakeDeleteUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, DeleteUserOutputDTO)
    assert presenter.response.user.id == target.id
    assert presenter.response.user.is_active is False


# ============================================================================
# NEGATIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_delete_user_self_deletion(uow_factory, initial_users):
    """Test admin cannot delete themselves."""
    target = initial_users[1]  # admin user
    auth_service = FakeAuthService(
        is_user_found=True,
        user_id=UserId.from_str(target.id),
    )
    use_case = DeleteUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = DeleteUserInputDTO(user_id=target.id)
    presenter = FakeDeleteUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.BAD_REQUEST
    assert isinstance(presenter.response, str)
    assert "cannot delete themselves" in presenter.response.lower()


@pytest.mark.asyncio
async def test_delete_user_not_found(uow_factory):
    """Test deleting non-existent user returns NOT_FOUND."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = DeleteUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = DeleteUserInputDTO(user_id=str(UserId.new()))
    presenter = FakeDeleteUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.NOT_FOUND
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_delete_user_already_inactive(uow_factory, initial_users):
    """Test deleting already inactive user returns DOMAIN_ERROR."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = DeleteUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target = initial_users[0]

    # First deletion should succeed
    dto = DeleteUserInputDTO(user_id=target.id)
    presenter = FakeDeleteUserPresenter()
    await use_case.execute(dto, presenter)
    assert presenter.state is State.OK

    # Second deletion should fail
    presenter2 = FakeDeleteUserPresenter()
    await use_case.execute(dto, presenter2)

    assert presenter2.state is State.DOMAIN_ERROR
    assert isinstance(presenter2.response, str)


@pytest.mark.asyncio
async def test_delete_user_invalid_uuid(uow_factory):
    """Test invalid UUID returns DOMAIN_ERROR."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = DeleteUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = DeleteUserInputDTO(user_id="not-a-uuid")
    presenter = FakeDeleteUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.DOMAIN_ERROR
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_delete_user_unauthorized():
    """Test unauthenticated request returns UNAUTHORIZED."""
    auth_service = FakeAuthService(is_user_found=False)

    def uow_factory():
        return FakeUoW(initial_users=[])

    use_case = DeleteUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = DeleteUserInputDTO(user_id=str(UserId.new()))
    presenter = FakeDeleteUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.UNAUTHORIZED
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_delete_user_forbidden_for_regular_user():
    """Test regular user cannot delete users."""
    auth_service = FakeAuthService(is_user_found=True, user_role=UserRole.USER)

    def uow_factory():
        return FakeUoW(initial_users=[])

    use_case = DeleteUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = DeleteUserInputDTO(user_id=str(UserId.new()))
    presenter = FakeDeleteUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.FORBIDDEN
    assert isinstance(presenter.response, str)
