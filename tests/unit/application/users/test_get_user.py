"""Unit tests for GetUser use case."""

import pytest

from app.application.dto import GetUserInputDTO, GetUserOutputDTO
from app.application.ports import State
from app.application.use_cases.get_user import GetUserUseCase

from tests.adapters import FakeAuthService, FakeGetUserPresenter, FakeUoW


# ============================================================================
# POSITIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_success(
    uow_factory,
    initial_users,
):
    """Test successful retrieval of a user by ID."""
    auth_service = FakeAuthService(is_user_found=True)

    use_case = GetUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target_user = initial_users[0]
    dto = GetUserInputDTO(user_id=target_user.id)
    presenter = FakeGetUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, GetUserOutputDTO)
    assert presenter.response.user.id == target_user.id
    assert presenter.response.user.username == target_user.username
    assert presenter.response.user.role == target_user.role


@pytest.mark.asyncio
async def test_get_user_returns_correct_fields(
    uow_factory,
    initial_users,
):
    """Test that returned user DTO has all expected fields."""
    auth_service = FakeAuthService(is_user_found=True)

    use_case = GetUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target_user = initial_users[0]
    dto = GetUserInputDTO(user_id=target_user.id)
    presenter = FakeGetUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, GetUserOutputDTO)

    user_dto = presenter.response.user
    assert isinstance(user_dto.id, str)
    assert isinstance(user_dto.username, str)
    assert isinstance(user_dto.role, str)
    assert isinstance(user_dto.is_active, bool)


@pytest.mark.asyncio
async def test_get_user_no_password_leak(
    uow_factory,
    initial_users,
):
    """Test that password hash is not leaked in response DTO."""
    auth_service = FakeAuthService(is_user_found=True)

    use_case = GetUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    target_user = initial_users[0]
    dto = GetUserInputDTO(user_id=target_user.id)
    presenter = FakeGetUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.OK
    assert isinstance(presenter.response, GetUserOutputDTO)

    user_dto = presenter.response.user
    assert not hasattr(user_dto, "password")
    assert not hasattr(user_dto, "password_hash")
    assert not hasattr(user_dto, "raw_password")


# ============================================================================
# NEGATIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_not_found(
    uow_factory,
):
    """Test that non-existent user ID returns NOT_FOUND."""
    from app.domain.value_objects import UserId

    auth_service = FakeAuthService(is_user_found=True)

    use_case = GetUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    non_existent_id = str(UserId.new())
    dto = GetUserInputDTO(user_id=non_existent_id)
    presenter = FakeGetUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.NOT_FOUND
    assert isinstance(presenter.response, str)
    assert "not found" in presenter.response.lower()


@pytest.mark.asyncio
async def test_get_user_invalid_uuid_format(
    uow_factory,
):
    """Test that invalid UUID format returns DOMAIN_ERROR."""
    auth_service = FakeAuthService(is_user_found=True)

    use_case = GetUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = GetUserInputDTO(user_id="not-a-valid-uuid")
    presenter = FakeGetUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.DOMAIN_ERROR
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_get_user_empty_uuid(
    uow_factory,
):
    """Test that empty UUID string returns DOMAIN_ERROR."""
    auth_service = FakeAuthService(is_user_found=True)

    use_case = GetUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    dto = GetUserInputDTO(user_id="")
    presenter = FakeGetUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.DOMAIN_ERROR
    assert isinstance(presenter.response, str)


@pytest.mark.asyncio
async def test_get_user_unauthorized():
    """Test that unauthenticated request returns UNAUTHORIZED."""
    auth_service = FakeAuthService(is_user_found=False)

    def uow_factory():
        return FakeUoW(initial_users=[])

    use_case = GetUserUseCase(
        auth_service=auth_service,
        uow_factory=uow_factory,
    )

    from app.domain.value_objects import UserId

    dto = GetUserInputDTO(user_id=str(UserId.new()))
    presenter = FakeGetUserPresenter()

    await use_case.execute(dto, presenter)

    assert presenter.state is State.UNAUTHORIZED
    assert isinstance(presenter.response, str)
