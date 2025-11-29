from __future__ import annotations

from app.application.dto.base import DTO
from app.application.ports import AuthPresenter
from app.application.ports.presenters import Presenter


class FastAPIPresenter[D: DTO](Presenter[D]):
    """Generic FastAPI presenter."""


class FastAPIAuthPresenter[D: DTO](AuthPresenter[D]):
    """Generic FastAPI auth presenter."""
