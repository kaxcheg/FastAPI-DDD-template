from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.base import Entity
from app.domain.exceptions.base import DomainError
from app.domain.services import IdGenerator
from app.domain.value_objects import UserId, Username, UserPasswordHash, UserRole


@dataclass(eq=False, kw_only=True)
class User(Entity[UserId]):
    """Domain user entity.

    Args:
        id: Immutable identifier.
        username: Unique username.
        password_hash: Secure password hash.
        role: Current role.
        is_active: Activity flag.
    """

    username: Username
    password_hash: UserPasswordHash
    role: UserRole
    is_active: bool = True

    # ---------- Factory ----------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        username: Username,
        password_hash: UserPasswordHash,
        role: UserRole,
        id_gen: IdGenerator,
    ) -> User:
        """Create a new user with generated id.

        Args:
            username: Unique username.
            password_hash: Secure password hash.
            role: User role.
            id_gen: Identifier generator.

        Returns:
            User: Newly created entity.
        """
        return cls(
            id=id_gen.new(),
            username=username,
            password_hash=password_hash,
            role=role,
        )

    @classmethod
    def from_storage(
        cls,
        *,
        id: UserId,
        username: Username,
        password_hash: UserPasswordHash,
        role: UserRole,
        is_active: bool = True,
    ) -> User:
        """Rehydrate user from storage.

        Args:
            id: Persistent identifier.
            username: Stored username.
            password_hash: Stored password hash.
            role: Stored role.
            is_active: Stored activity flag.

        Returns:
            User: Rehydrated entity.
        """
        return cls(
            id=id,
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )

    def is_admin(self) -> bool:
        """Return True if user holds admin role."""
        return self.role is UserRole.ADMIN

    def change_username(self, new: Username) -> None:
        """Set new username or raise if identical.

        Raises:
            DomainError: When username is unchanged.
        """
        if new == self.username:
            raise DomainError("New username is identical to current.")
        self.username = new  # type: ignore[misc]

    def change_password(self, new_hash: UserPasswordHash) -> None:
        """Set new password hash or raise if identical.

        Raises:
            DomainError: When hash is unchanged.
        """
        if new_hash == self.password_hash:
            raise DomainError("New password hash matches the old one.")
        self.password_hash = new_hash  # type: ignore[misc]

    def change_role(self, new: UserRole) -> None:
        """Set new role or raise if identical.

        Raises:
            DomainError: When role is unchanged.
        """
        if new == self.role:
            raise DomainError("Role is already set to the given value.")
        self.role = new  # type: ignore[misc]
        if self.role is UserRole.ADMIN:
            self.is_active = True  # type: ignore[misc]

    def activate(self) -> None:
        """Activate account or raise if already active.

        Raises:
            DomainError: When already active.
        """
        if self.is_active:
            raise DomainError("User is already active.")
        self.is_active = True  # type: ignore[misc]

    def deactivate(self) -> None:
        """Deactivate account or raise if already inactive.

        Raises:
            DomainError: When already inactive.
        """
        if not self.is_active:
            raise DomainError("User is already inactive.")
        self.is_active = False  # type: ignore[misc]
