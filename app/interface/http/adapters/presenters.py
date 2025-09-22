from __future__ import annotations

from app.application.dto import AuthResponseDTO, CreateUserOutputDTO
from app.application.ports import AuthPresenter
from app.application.ports.presenters import Presenter


class FastAPICreateUserPresenter(AuthPresenter[CreateUserOutputDTO]):
    """Presenter for create-user responses."""


class FastAPIAuthenticationPresenter(Presenter[AuthResponseDTO]):
    """Presenter for authentication responses."""
