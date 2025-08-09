from __future__ import annotations

from typing import override

from app.application.dto import AuthResponseDTO, CreateUserOutputDTO
from app.application.ports import AuthPresenter
from app.application.ports.presenters import Presenter, State


class FastAPICreateUserPresenter(AuthPresenter[CreateUserOutputDTO]):
    """Presenter for create-user responses."""

    def __init__(self) -> None:
        """Initialize default state and response."""
        self._state: State = State.ERROR
        self.response: CreateUserOutputDTO | str = ""

    @property
    @override
    def state(self) -> State:
        """Return current presenter state."""
        return self._state

    @override
    def ok(self, dto: CreateUserOutputDTO) -> None:
        """Set success state and DTO."""
        self._state = State.OK
        self.response = dto

    @override
    def conflict(self, message: str) -> None:
        """Set conflict state with message."""
        self._state = State.CONFLICT
        self.response = message

    @override
    def error(self, message: str) -> None:
        """Set error state with message."""
        self._state = State.ERROR
        self.response = message

    @override
    def unauthorized(self, message: str) -> None:
        """Set unauthorized state with message."""
        self._state = State.UNAUTHORIZED
        self.response = message

    @override
    def forbidden(self, message: str) -> None:
        """Set forbidden state with message."""
        self._state = State.FORBIDDEN
        self.response = message


class FastAPIAuthenticationPresenter(Presenter[AuthResponseDTO]):
    """Presenter for authentication responses."""

    def __init__(self) -> None:
        """Initialize default state and response."""
        self._state: State = State.ERROR
        self.response: AuthResponseDTO | str = ""

    @property
    @override
    def state(self) -> State:
        """Return current presenter state."""
        return self._state

    @override
    def ok(self, dto: AuthResponseDTO) -> None:
        """Set success state and DTO."""
        self._state = State.OK
        self.response = dto

    @override
    def error(self, message: str) -> None:
        """Set error state with message."""
        self._state = State.ERROR
        self.response = message

    @override
    def conflict(self, message: str) -> None:
        """Set conflict state with message."""
        self._state = State.CONFLICT
        self.response = message

    @override
    def unauthorized(self, message: str) -> None:
        """Set unauthorized state with message."""
        self._state = State.UNAUTHORIZED
        self.response = message
