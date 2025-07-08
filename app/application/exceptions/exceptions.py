from app.application.exceptions.base import ApplicationError

class DuplicateUserError(ApplicationError):
    pass

class NotAuthenticatedError(ApplicationError):
    pass
    
class NotAuthorizedError(ApplicationError):
    pass
