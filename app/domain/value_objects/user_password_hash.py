from __future__ import annotations

from dataclasses import dataclass
from typing import override

from app.domain.exceptions import ValueObjectError
from app.domain.value_objects.base import ValueObject
from app.domain.value_objects.constants import HASH_LEN


@dataclass(frozen=True, repr=False)
class UserPasswordHash(ValueObject):
    """Password hash value object.

    Args:
        value: Password hash bytes.

    Raises:
        ValueObjectError: If hash is empty or length differs from HASH_LEN.
    """

    value: bytes

    @override
    def __post_init__(self) -> None:
        """Validate hash length."""
        super().__post_init__()
        if not self.value:
            raise ValueObjectError("Password hash must not be empty.")
        if len(self.value) != HASH_LEN:
            raise ValueObjectError(f"Password hash must be {HASH_LEN} bytes.")

    @override
    def __repr__(self) -> str:
        """Return class name only."""
        return f"{type(self).__name__}"
