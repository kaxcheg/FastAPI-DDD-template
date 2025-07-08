class DomainError(Exception):
    """
    Exception for violations of fundamental domain rules, such as attempts to change
    the immutable `id` of an Entity, as well as for complex business rule violations.

    Not for:
    - Single attribute validation (use `DomainFieldError` instead).
    - Application, infrastructure, or system errors.
    """


