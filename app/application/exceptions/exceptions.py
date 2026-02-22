from app.application.exceptions.base import ApplicationError


class NotAuthenticatedError(ApplicationError):
    """Adapters should raise and use cases should handle this exception, if user is not authenticated."""


class NotAuthorizedError(ApplicationError):
    """Adapters should raise and use cases should handle this exception, if user is not authorized."""
