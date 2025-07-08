from app.domain.value_objects import UserId, Username, UserRole
from app.domain.entities.user import User 

from app.application.dto import CredentialDTO
from app.application.ports.services import AuthService
from app.application.exceptions import NotAuthenticatedError, NotAuthorizedError

from app.infrastructure.db.sqlalchemy.adapters import UserRepositorySQL
from app.config import settings
from jwt import decode, encode
from jwt.exceptions import InvalidTokenError

class TokenSQLAuthService(AuthService[UserRepositorySQL]):
    """Facade over JWT / session store."""
    credentials: CredentialDTO
    def ensure_role(self, user_id: UserId, role: UserRole, target_role: UserRole) -> None:
        if role != target_role:
            raise NotAuthorizedError("Forbidden")

    async def current_user(self, repo: UserRepositorySQL) -> User:
        try:
            assert isinstance(self.credentials.value, str) 
            payload:dict = decode(
                self.credentials.value,    # token str
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"require": ["sub", "role", "exp"]}
                )      
        except (InvalidTokenError, AssertionError):
            raise NotAuthenticatedError("Unauthorized")
        
        user_id = payload.get("sub", None)
        role = payload.get("role", None)

        if not user_id or not role or not isinstance(user_id, str) or not isinstance(role, str):
            raise NotAuthenticatedError("Unauthorized")
        
        user = await repo.get_by_id(UserId.from_str(user_id))
        if user is None:
            raise NotAuthenticatedError("Unauthorized")
        
        return user