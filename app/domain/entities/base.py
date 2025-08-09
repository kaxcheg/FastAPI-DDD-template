from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Any, Protocol, override

from app.domain.exceptions.base import DomainError
from app.domain.value_objects.base import ValueObject


@dataclass(eq=False, kw_only=True)
class Entity[T: ValueObject](ABC):
    """Domain entity identified by an immutable id.

    Args:
        id: Immutable identifier of the entity.
    """

    id: T

    @override
    def __setattr__(self, name: str, value: Any) -> None:
        """Block changing id after initialization."""
        if name == "id" and getattr(self, "id", None) is not None:
            raise DomainError("Changing entity ID is not permitted.")
        super().__setattr__(name, value)

    @override
    def __eq__(self, other: Any) -> bool:
        """Entities are equal when ids match."""
        return isinstance(other, type(self)) and other.id == self.id

    @override
    def __hash__(self) -> int:
        """Return hash of immutable id."""
        return hash(self.id)


class Repository(Protocol):
    """Domain repository interface."""
