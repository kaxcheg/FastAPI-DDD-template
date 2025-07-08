from enum import Enum, auto
from typing import Protocol, TypeVar

from app.application.dto.base import DTO


class State(Enum):
    OK = auto()
    ERROR = auto()
    UNAUTHORIZED = auto()
    FORBIDDEN = auto()
    CONFLICT = auto()

D = TypeVar("D", bound=DTO)

class Presenter(Protocol[D]):
    """Generic presenter that handles success/failure output."""
    _state: State
    response: D | str
    def ok(self, dto: D) -> None: ...
    def error(self, message: str) -> None: ...
    def conflict(self, message: str) -> None: ...
    def unauthorized(self, message: str) -> None: ...

    @property
    def state(self) -> State:
        return self._state

class AuthPresenter(Presenter[D]):
    def forbidden(self, message: str) -> None: ...
