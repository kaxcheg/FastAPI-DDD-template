from __future__ import annotations

from enum import Enum, auto
from typing import Protocol, runtime_checkable

from app.application.dto.base import DTO


class State(Enum):
    """Operation result states."""
    OK = auto()
    ERROR = auto()
    UNAUTHORIZED = auto()
    FORBIDDEN = auto()
    CONFLICT = auto()

@runtime_checkable
class Presenter[D: DTO](Protocol):
    """Presenter contract that emits success or failure output."""

    _state: State
    response: D | str

    def ok(self, dto: D, /) -> None: ...
    def error(self, message: str, /) -> None: ...
    def conflict(self, message: str, /) -> None: ...
    def unauthorized(self, message: str, /) -> None: ...

    @property
    def state(self) -> State: ...


class AuthPresenter[D: DTO](Presenter[D]):
    """Presenter with extra forbidden handler."""

    def forbidden(self, message: str) -> None: ...
