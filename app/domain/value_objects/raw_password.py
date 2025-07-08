from dataclasses import dataclass
from app.domain.value_objects.base import ValueObject
from app.domain.exceptions import ValueObjectError
from app.domain.value_objects.constants import RAW_PASSWORD_MAX_LEN, RAW_PASSWORD_MIN_LEN, HASH_LEN

@dataclass(frozen=True, repr=False)
class UserRawPassword(ValueObject):
    """raises DomainFieldError if hash is not valid"""
    value: str

    def __post_init__(self) -> None:
        """
        Ensures the passwords is non-empty and matches the expected length.
        """
        super().__post_init__()
        if not self.value:
            raise ValueObjectError("Password must not be empty.")
        if  len(self.value) < RAW_PASSWORD_MIN_LEN or len(self.value) > RAW_PASSWORD_MAX_LEN:
            raise ValueObjectError(
                f"Password must be {RAW_PASSWORD_MIN_LEN}-{RAW_PASSWORD_MAX_LEN} symbols.",
            )

    def __repr__(self) -> str:
        return f"{type(self).__name__}"