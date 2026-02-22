from __future__ import annotations

from app.domain.exceptions import DuplicateUsernameError
from app.domain.repositories import UserRepository
from app.domain.value_objects import UserId, Username


class UserInvariantService:
    """Cross-aggregate invariant checks for User.

    Args:
        repo: User repository for existence lookups.
    """

    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def ensure_username_unique(
        self,
        username: Username,
        exclude_user_id: UserId | None = None,
    ) -> None:
        """Verify that *username* is not already taken.

        Args:
            username: Username to check.
            exclude_user_id: Skip this user (useful for updates).

        Raises:
            DuplicateUsernameError: When username is already in use.
        """
        existing = await self._repo.get_by_username(username)
        if existing is not None and (
            exclude_user_id is None or existing.id != exclude_user_id
        ):
            raise DuplicateUsernameError(f"Username '{username}' is already taken.")
