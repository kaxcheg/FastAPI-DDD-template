import pytest

from app.domain.value_objects import UserRole

from app.application.dto.base import DTO
from app.application.ports.presenters import AuthPresenter, State
from app.application.use_cases import AuthorizeUserUseCase

from tests.adapters import FakeAuthService, FakeAuthorizationPresenter


class TestAuthorizeUseCase(AuthorizeUserUseCase[DTO, DTO]):
    _required_roles = [UserRole.ADMIN]
    async def run(self, dto: DTO, presenter: AuthPresenter[DTO]) -> None:
        presenter.ok(dto)

@pytest.mark.asyncio
async def test_authorize_success(uow_factory):
    """Test authentication fails with wrong password."""
    
    auth_service = FakeAuthService(is_user_found=True)

    uc = TestAuthorizeUseCase(auth_service)

    presenter = FakeAuthorizationPresenter()
    dto = DTO()
    await uc.execute(dto, presenter)
    
    assert presenter.state == State.OK
    assert presenter.response == dto 

@pytest.mark.asyncio
async def test_authorize_user_not_authenticated(uow_factory):
    """Test authorization fails when user is not authenticated."""
    auth_service = FakeAuthService(
        is_user_found=False,
    )
    uc = TestAuthorizeUseCase(auth_service)
    presenter = FakeAuthorizationPresenter()
    
    await uc.execute(DTO(), presenter)
    
    assert presenter.state == State.UNAUTHORIZED
    assert presenter.response == "Not authorized"

@pytest.mark.asyncio
async def test_authorize_insufficient_role(uow_factory):
    """Test authorization fails when user has insufficient role."""
    
    auth_service = FakeAuthService(
        is_user_found=True,
        user_role=UserRole.USER
    )
    
    uc = TestAuthorizeUseCase(auth_service)
    presenter = FakeAuthorizationPresenter()
    
    await uc.execute(DTO(), presenter)
    
    assert presenter.state == State.FORBIDDEN
    assert presenter.response == "Forbidden"
