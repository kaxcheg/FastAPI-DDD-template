from dataclasses import dataclass
from uuid import UUID, uuid4 

from app.domain.value_objects.base import ValueObject

@dataclass(frozen=True, repr=False)
class UserId(ValueObject):
    value: UUID

    def __str__(self) -> str:
        return str(self.value)

    @staticmethod
    def new() -> "UserId":
        return UserId(uuid4())
    
    @staticmethod
    def from_str(v: str) -> "UserId":
        return UserId(UUID(v))
    
    