from __future__ import annotations

from dataclasses import dataclass
from typing import override
from uuid import UUID, uuid4

from app.domain.value_objects.base import ValueObject


@dataclass(frozen=True, repr=False)
class UserId(ValueObject):
    """User identifier value object.

    Args:
        value: UUID value.
    """

    value: UUID

    @override
    def __str__(self) -> str:
        """Return UUID as string.

        Returns:
            str: UUID in canonical form.
        """
        return str(self.value)

    @staticmethod
    def new() -> UserId:
        """Generate random identifier.

        Returns:
            UserId: Newly generated identifier.
        """
        return UserId(uuid4())

    @staticmethod
    def from_str(v: str) -> UserId:
        """Construct identifier from string.

        Args:
            v: UUID string.

        Returns:
            UserId: Identifier built from the string.
        """
        return UserId(UUID(v))
