from __future__ import annotations

from dataclasses import dataclass
from typing import override

from app.domain.exceptions import ValueObjectError
from app.domain.value_objects.base import ValueObject
from app.domain.value_objects.constants import (
    RAW_PASSWORD_MAX_LEN,
    RAW_PASSWORD_MIN_LEN,
)


@dataclass(frozen=True, repr=False)
class UserRawPassword(ValueObject):
    """User password in plain text.

    Args:
        value: Raw password string.

    Raises:
        ValueObjectError: If value is empty or its length is out of bounds.
    """

    value: str

    @override
    def __post_init__(self) -> None:
        """Validate value length."""
        super().__post_init__()
        length = len(self.value)
        if length == 0:
            raise ValueObjectError("Password must not be empty.")
        if not RAW_PASSWORD_MIN_LEN <= length <= RAW_PASSWORD_MAX_LEN:
            raise ValueObjectError(
                f"Password length must be {RAW_PASSWORD_MIN_LEN}-{RAW_PASSWORD_MAX_LEN} symbols."
            )

    @override
    def __repr__(self) -> str:
        """Return class name only."""
        return f"{type(self).__name__}"
