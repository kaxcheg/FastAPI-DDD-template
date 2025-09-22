from app.application.exceptions.base import ApplicationError


class DuplicateUserError(ApplicationError):
    """Adapters should raise and use cases should handle this exception, if adding to repo existing user."""


class NotAuthenticatedError(ApplicationError):
    """Adapters should raise and use cases should handle this exception, if user is not authenticated."""


class NotAuthorizedError(ApplicationError):
    """Adapters should raise and use cases should handle this exception, if user is not authorized."""
