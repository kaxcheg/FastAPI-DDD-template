from __future__ import annotations

from abc import ABC
from dataclasses import asdict, dataclass, fields
from typing import Any, override

from app.domain.exceptions import ValueObjectError


@dataclass(frozen=True, repr=False)
class ValueObject(ABC):
    """Immutable value object base type."""

    def __post_init__(self) -> None:
        """Ensure at least one field exists.

        Raises:
            ValueObjectError: When the dataclass has no fields.
        """
        if not fields(self):
            raise ValueObjectError(
                f"{type(self).__name__} must have at least one field!"
            )

    @override
    def __repr__(self) -> str:
        """Return a compact textual representation.

        Returns:
            str: Class name and field values.
        """
        return f"{type(self).__name__}({self._repr_value()})"

    def _repr_value(self) -> str:
        """Build the inner representation used by __repr__.

        Returns:
            str: Field value string.
        """
        all_fields = fields(self)
        if len(all_fields) == 1:
            return repr(getattr(self, all_fields[0].name))
        return ", ".join(f"{f.name}={getattr(self, f.name)!r}" for f in all_fields)

    def get_fields(self) -> dict[str, Any]:
        """Return all field values as a dict.

        Returns:
            dict[str, Any]: Mapping of field names to values.
        """
        return asdict(self)
