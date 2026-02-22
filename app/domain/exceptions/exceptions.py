from app.domain.exceptions.base import DomainError


class ValueObjectError(DomainError):
    """
    Exception for validation errors in Value Objects:
    1. Violations of Value Object invariants during creation.
    2. Single-field validation errors in Entities.
    """


class DuplicateUsernameError(DomainError):
    """Username uniqueness invariant violated."""
