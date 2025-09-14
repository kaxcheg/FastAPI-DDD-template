import pytest

from app.domain.entities.user.repo import UserRepository
from app.domain.value_objects import UserRole, Username

from app.application.dto import CreateUserInputDTO, CreateUserOutputDTO
from app.application.ports import UnitOfWork, State
from app.application.use_cases import CreateUserUseCase

from tests.adapters import FakeCreateUserPresenter

@pytest.mark.asyncio
async def test_create_user_success(
    successful_auth_service,
    uow_factory,
    password_hasher,
    id_generator,
):
    """Test successful user creation by admin."""

    use_case = CreateUserUseCase(
        auth_service=successful_auth_service,
        uow_factory=uow_factory,
        hasher=password_hasher,
        id_gen=id_generator
    )
    
    dto = CreateUserInputDTO(
        username="new_user",
        password="secure_password123",
        role=UserRole.USER
    )
    presenter = FakeCreateUserPresenter()
    
    await use_case.execute(dto, presenter)
    
    assert presenter.state is State.OK
    assert isinstance(presenter.response, CreateUserOutputDTO)
    assert presenter.response.username == dto.username
    assert presenter.response.role == dto.role
    
    async with uow_factory() as uow:
        uow: UnitOfWork
        repo = uow.get_repo(UserRepository)
        new_user = repo.get_by_username(Username(dto.username))
    
    assert new_user is not None


@pytest.mark.asyncio
async def test_create_user_conflict(
    successful_auth_service,
    uow_factory,
    password_hasher,
    id_generator,
    initial_users
):
    """Test user creation fails when username already exists."""

    use_case = CreateUserUseCase(
        auth_service=successful_auth_service,
        uow_factory=uow_factory,
        hasher=password_hasher,
        id_gen=id_generator
    )
    
    existing_user = initial_users[0]
    dto = CreateUserInputDTO(
        username=existing_user.username,
        password="password123",
        role=UserRole.USER
    )
    presenter = FakeCreateUserPresenter()
    
    await use_case.execute(dto, presenter)
    
    assert presenter.state == State.CONFLICT
    assert presenter.response == "Username already exists"


@pytest.mark.asyncio
async def test_create_user_validation_error(
    successful_auth_service,
    uow_factory,
    password_hasher,
    id_generator
):
    """Test user creation fails with invalid input data."""

    use_case = CreateUserUseCase(
        auth_service=successful_auth_service,
        uow_factory=uow_factory,
        hasher=password_hasher,
        id_gen=id_generator
    )
    
    dto = CreateUserInputDTO(
        username="",
        password="password123",
        role=UserRole.USER
    )
    presenter = FakeCreateUserPresenter()
    
    await use_case.execute(dto, presenter)
    
    assert presenter.state == State.ERROR
    assert isinstance(presenter.response, str)
    assert "User with provided parameters cannot be created" in presenter.response


@pytest.mark.asyncio
async def test_create_user_invalid_role(
    successful_auth_service,
    uow_factory,
    password_hasher,
    id_generator
):
    """Test user creation fails with invalid role."""

    use_case = CreateUserUseCase(
        auth_service=successful_auth_service,
        uow_factory=uow_factory,
        hasher=password_hasher,
        id_gen=id_generator
    )
    
    dto = CreateUserInputDTO(
        username="new_user",
        password="password123",
        role="INVALID_ROLE"
    )
    presenter = FakeCreateUserPresenter()
    
    await use_case.execute(dto, presenter)
    
    assert presenter.state == State.ERROR
    assert isinstance(presenter.response, str)
    assert "User with provided parameters cannot be created" in presenter.response


@pytest.mark.asyncio
async def test_create_user_empty_password(
    successful_auth_service,
    uow_factory,
    password_hasher,
    id_generator
):
    """Test user creation fails with empty password."""

    use_case = CreateUserUseCase(
        auth_service=successful_auth_service,
        uow_factory=uow_factory,
        hasher=password_hasher,
        id_gen=id_generator
    )
    
    dto = CreateUserInputDTO(
        username="new_user",
        password="",
        role=UserRole.USER
    )
    presenter = FakeCreateUserPresenter()
    
    await use_case.execute(dto, presenter)
    
    assert presenter.state == State.ERROR
    assert isinstance(presenter.response, str)
    assert "User with provided parameters cannot be created" in presenter.response