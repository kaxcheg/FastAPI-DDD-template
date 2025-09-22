from __future__ import annotations

from dataclasses import dataclass
from typing import override

from app.domain.exceptions import ValueObjectError
from app.domain.value_objects.base import ValueObject
from app.domain.value_objects.constants import USERNAME_MAX_LEN, USERNAME_MIN_LEN


def validate_username_length(username_value: str) -> None:
    """Raise if username length is out of bounds.

    Args:
        username_value: Raw username string.

    Raises:
        ValueObjectError: When length is outside allowed range.
    """
    if not USERNAME_MIN_LEN <= len(username_value) <= USERNAME_MAX_LEN:
        raise ValueObjectError(
            f"Username must be between {USERNAME_MIN_LEN} and {USERNAME_MAX_LEN} characters."
        )


@dataclass(frozen=True, repr=False)
class Username(ValueObject):
    """Username value object.

    Args:
        value: Raw username string.

    Raises:
        ValueObjectError: If length is out of bounds.
    """

    value: str

    @override
    def __post_init__(self) -> None:
        """Validate value length."""
        super().__post_init__()
        validate_username_length(self.value)

    @override
    def __str__(self) -> str:
        """Return username string.

        Returns:
            str: Username.
        """
        return str(self.value)
