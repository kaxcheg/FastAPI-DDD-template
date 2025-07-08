from typing import Optional
from app.domain.entities.user import User
from app.domain.value_objects import UserId, Username
from app.domain.entities.base import Repository

class UserRepository(Repository):
    """User repository contract"""
    async def get_by_username(self, username: Username) -> Optional[User]: ...
    async def get_by_id(self, user_id: UserId) -> Optional[User]: ...
    async def add(self, user: User) -> None: ...

