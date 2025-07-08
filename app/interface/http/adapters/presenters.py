from app.application.dto import CreateUserOutputDTO, AuthRequestDTO, AuthResponseDTO
from app.application.ports.presenters import State
from app.application.ports import AuthPresenter
from app.application.ports.presenters import Presenter

class FastAPICreateUserPresenter(AuthPresenter[CreateUserOutputDTO]):
    def __init__(self) -> None:
        self.response: CreateUserOutputDTO | str

    def ok(self, dto: CreateUserOutputDTO) -> None:
        self._state = State.OK
        self.response = dto

    def conflict(self, message: str) -> None:
        self._state = State.CONFLICT
        self.response = message

    def error(self, message: str) -> None:
        self._state = State.ERROR
        self.response = message

    def unauthorized(self, message: str) -> None:
        """Called when credentials are invalid."""
        self._state = State.UNAUTHORIZED
        self.response = message

    def forbidden(self, message: str) -> None:
        """."""
        self._state = State.FORBIDDEN
        self.response = message

class FastAPIAuthenticationPresenter(Presenter[AuthResponseDTO]):
    def __init__(self) -> None:
        self.response: AuthResponseDTO | str
        
    def ok(self, dto: AuthResponseDTO) -> None:
        """Called when authentication succeeds."""
        self._state = State.OK
        self.response = dto

    def error(self, message: str) -> None:
        """Called on unexpected error."""
        self._state = State.ERROR
        self.response = message
    
    def conflict(self, message: str) -> None:
        self._state = State.CONFLICT
        self.response = message
    
    def unauthorized(self, message: str) -> None:
        """Called when credentials are invalid."""
        self._state = State.UNAUTHORIZED
        self.response = message
