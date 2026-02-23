from __future__ import annotations

from typing import NoReturn

from rest_framework.exceptions import (
    AuthenticationFailed,
    NotFound,
    ParseError,
    PermissionDenied,
    ValidationError,
)

from app.application.ports.presenters import Presenter, State


class ConflictError(Exception):
    """HTTP 409 Conflict."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def raise_for_presenter_state(p: Presenter) -> NoReturn:  # type: ignore[type-arg]
    """Convert presenter error state to a DRF exception.

    :raises ParseError: On BAD_REQUEST state.
    :raises AuthenticationFailed: On UNAUTHORIZED state.
    :raises PermissionDenied: On FORBIDDEN state.
    :raises ConflictError: On CONFLICT state.
    :raises NotFound: On NOT_FOUND state.
    :raises ValidationError: On DOMAIN_ERROR state.
    :raises ValueError: On unknown state.
    """
    if not isinstance(p.response, str):
        raise ValueError("Wrong type for presenter response. str expected.")
    match p.state:
        case State.BAD_REQUEST:
            raise ParseError(detail=p.response)
        case State.UNAUTHORIZED:
            raise AuthenticationFailed(detail=p.response)
        case State.FORBIDDEN:
            raise PermissionDenied(detail=p.response)
        case State.CONFLICT:
            raise ConflictError(detail=p.response)
        case State.NOT_FOUND:
            raise NotFound(detail=p.response)
        case State.DOMAIN_ERROR:
            raise ValidationError(detail=p.response)
    raise ValueError("Wrong presenter state")
