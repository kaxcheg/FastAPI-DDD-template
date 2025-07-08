from dataclasses import dataclass
from app.domain.value_objects.base import ValueObject
from app.domain.value_objects.constants import USERNAME_MAX_LEN, USERNAME_MIN_LEN
from app.domain.exceptions import ValueObjectError

def validate_username_length(username_value: str) -> None:
    if len(username_value) < USERNAME_MIN_LEN or len(username_value) > USERNAME_MAX_LEN:
            raise ValueObjectError(
                f"Username must be between "
                f"{USERNAME_MIN_LEN} and "
                f"{USERNAME_MAX_LEN} characters.",
            )

@dataclass(frozen=True, repr=False)
class Username(ValueObject):
    """raises DomainFieldError"""

    value: str

    def __str__(self) -> str:
        return str(self.value)

    def __post_init__(self) -> None:
        """
        :raises DomainFieldError:
        """
        super().__post_init__()
        validate_username_length(self.value)