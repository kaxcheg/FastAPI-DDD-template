# app/domain/value_objects/user_password_hash.py
from dataclasses import dataclass
from app.domain.value_objects.base import ValueObject
from app.domain.exceptions import ValueObjectError
from app.domain.value_objects.constants import HASH_LEN

@dataclass(frozen=True, repr=False)
class UserPasswordHash(ValueObject):
    """raises DomainFieldError if hash is not valid"""
    value: bytes

    def __post_init__(self) -> None:
        """
        Ensures the hash is non-empty and matches the expected length.
        """
        super().__post_init__()
        if not self.value:
            raise ValueObjectError("Password hash must not be empty.")
        if len(self.value) != HASH_LEN:
            raise ValueObjectError(
                f"Password hash must be {HASH_LEN} bytes.",
            )

    def __repr__(self) -> str:
        return f"{type(self).__name__}"
