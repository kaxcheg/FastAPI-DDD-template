"""Unit tests for UpdateUser use case."""

import pytest

from app.application.dto import UpdateUserInputDTO, UpdateUserOutputDTO
from app.application.ports import State
from app.application.use_cases.update_user import UpdateUserUseCase
from app.domain.value_objects import UserId, UserRole

from tests.adapters import FakeAuthService, FakeUpdateUserPresenter, FakeUoW


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_update_user_username_success(uow_factory, initial_users):
    """Test admin can update a user's username."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target = initial_users[0]
    dto = UpdateUserInputDTO(user_id=target.id, username="new_username")
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, UpdateUserOutputDTO)
    assert presenter.response.user.username == "new_username"
    assert presenter.response.user.id == target.id


@pytest.mark.asyncio
async def test_update_user_role_success(uow_factory, initial_users):
    """Test admin can update a user's role."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target = initial_users[0]  # role is USER
    dto = UpdateUserInputDTO(user_id=target.id, role="admin")
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, UpdateUserOutputDTO)
    assert presenter.response.user.role == "admin"


@pytest.mark.asyncio
async def test_update_user_multiple_fields(uow_factory, initial_users):
    """Test admin can update multiple fields at once."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target = initial_users[1]  # admin user
    dto = UpdateUserInputDTO(
        user_id=target.id, username="multi_upd", role="user",
    )
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, UpdateUserOutputDTO)
    assert presenter.response.user.username == "multi_upd"
    assert presenter.response.user.role == "user"


# ============================================================================
# NEGATIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_update_user_not_found(uow_factory):
    """Test updating non-existent user returns NOT_FOUND."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = UpdateUserInputDTO(user_id=str(UserId.new()), username="whatever")
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.NOT_FOUND
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_update_user_no_fields(uow_factory, initial_users):
    """Test updating with no fields returns BAD_REQUEST."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target = initial_users[0]
    dto = UpdateUserInputDTO(user_id=target.id)
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.BAD_REQUEST
    assert isinstance(presenter.response, str)
    assert "No fields" in presenter.response


@pytest.mark.asyncio
async def test_update_user_same_username(uow_factory, initial_users):
    """Test setting same username returns DOMAIN_ERROR."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target = initial_users[0]
    dto = UpdateUserInputDTO(user_id=target.id, username=target.username)
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.DOMAIN_ERROR
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_update_user_duplicate_username(uow_factory, initial_users):
    """Test changing to existing username returns CONFLICT."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target = initial_users[0]
    other = initial_users[1]
    dto = UpdateUserInputDTO(user_id=target.id, username=other.username)
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.CONFLICT
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_update_user_invalid_role(uow_factory, initial_users):
    """Test invalid role returns DOMAIN_ERROR."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target = initial_users[0]
    dto = UpdateUserInputDTO(user_id=target.id, role="INVALID")
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.DOMAIN_ERROR
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_update_user_invalid_uuid(uow_factory):
    """Test invalid UUID returns DOMAIN_ERROR."""
    auth_service = FakeAuthService(is_user_found=True)
    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = UpdateUserInputDTO(user_id="not-a-uuid", username="whatever")
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.DOMAIN_ERROR
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_update_user_unauthorized():
    """Test unauthenticated request returns UNAUTHORIZED."""
    auth_service = FakeAuthService(is_user_found=False)

    def uow_factory():
        return FakeUoW(initial_users=[])

    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = UpdateUserInputDTO(user_id=str(UserId.new()), username="whatever")
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.UNAUTHORIZED
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_update_user_forbidden_for_regular_user():
    """Test regular user cannot update users."""
    auth_service = FakeAuthService(is_user_found=True, user_role=UserRole.USER)

    def uow_factory():
        return FakeUoW(initial_users=[])

    use_case = UpdateUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = UpdateUserInputDTO(user_id=str(UserId.new()), username="whatever")
    presenter = FakeUpdateUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.FORBIDDEN
    assert isinstance(presenter.response, str)
