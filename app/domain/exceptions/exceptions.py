from app.domain.exceptions.base import DomainError


class ValueObjectError(DomainError):
    """
    Exception for validation errors in Value Objects and Entity field values.

    Use cases:
    1. Violations of Value Object invariants during creation.
    2. Single-field validation errors in Entities.

    Not for:
    - Complex business rule violations (use `DomainError` instead).
    - Input validation at application boundaries.
    """