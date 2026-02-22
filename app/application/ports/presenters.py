from __future__ import annotations

from enum import Enum, auto
from typing import Protocol, runtime_checkable

from app.application.dto.base import DTO


class State(Enum):
    """Operation result states."""

    OK = auto()
    BAD_REQUEST = auto()
    DOMAIN_ERROR = auto()
    UNAUTHORIZED = auto()
    FORBIDDEN = auto()
    CONFLICT = auto()
    NOT_FOUND = auto()


@runtime_checkable
class Presenter[D: DTO](Protocol):
    """Presenter contract that emits success or failure output."""

    _state: State | None
    response: D | str

    def __init__(self) -> None:
        self._state = None

    @property
    def state(self) -> State | None:
        """Return current presenter state."""
        return self._state

    def ok(self, dto: D) -> None:
        """Set success state and DTO."""
        self._state = State.OK
        self.response = dto

    def bad_request(self, message: str) -> None:
        """Set bad-request state with message."""
        self._state = State.BAD_REQUEST
        self.response = message

    def domain_error(self, message: str) -> None:
        """Set error state with message."""
        self._state = State.DOMAIN_ERROR
        self.response = message

    def conflict(self, message: str) -> None:
        """Set conflict state with message."""
        self._state = State.CONFLICT
        self.response = message

    def not_found(self, message: str) -> None:
        """Set not-found state with message."""
        self._state = State.NOT_FOUND
        self.response = message

    def unauthorized(self, message: str) -> None:
        """Set unauthorized state with message."""
        self._state = State.UNAUTHORIZED
        self.response = message


class AuthPresenter[D: DTO](Presenter[D]):
    """Presenter with extra forbidden handler."""

    def forbidden(self, message: str) -> None:
        """Set forbidden state with message."""
        self._state = State.FORBIDDEN
        self.response = message
