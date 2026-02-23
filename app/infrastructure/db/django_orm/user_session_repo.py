from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from django.db.models import Q

from app.domain.repositories import Repository
from app.infrastructure.db.django_orm.models.user import UserModel
from app.infrastructure.db.django_orm.models.user_sessions import UserSessionModel


class UserSessionDjangoRepo(Repository):
    """Django ORM repository for user session management."""

    @staticmethod
    def _utcnow() -> datetime:
        """Always return timezone-aware UTC."""
        return datetime.now(timezone.utc)

    async def get_user_if_session_valid(
        self, user_id: UUID, session_id: UUID
    ) -> UserModel | None:
        """Return user if they have a valid (non-revoked, non-expired) session.

        Args:
            user_id: User identifier.
            session_id: Session identifier.

        Returns:
            UserModel or None.
        """
        try:
            return await UserModel.objects.filter(
                id=user_id,
                is_active=True,
                sessions__id=session_id,
                sessions__revoked_at__isnull=True,
                sessions__expires_at__gt=self._utcnow(),
            ).aget()
        except UserModel.DoesNotExist:
            return None

    async def get_session_by_id(self, session_id: UUID) -> UserSessionModel | None:
        """Return session by ID or None."""
        try:
            return await UserSessionModel.objects.aget(id=session_id)
        except UserSessionModel.DoesNotExist:
            return None

    async def get_user_valid_session_by_refresh_token(
        self, refresh_token_hash: str
    ) -> tuple[UserModel, UserSessionModel] | tuple[None, None]:
        """Find user and session by refresh token hash.

        Args:
            refresh_token_hash: SHA-256 hash of refresh token.

        Returns:
            Tuple of (UserModel, UserSessionModel) if found, else (None, None).
        """
        try:
            session = await UserSessionModel.objects.select_related("user").aget(
                refresh_token_hash=refresh_token_hash,
                revoked_at__isnull=True,
                expires_at__gt=self._utcnow(),
            )
        except UserSessionModel.DoesNotExist:
            return None, None

        user = session.user  # type: ignore[union-attr]
        if not user.is_active:
            return None, None
        return user, session

    async def create(
        self,
        user_id: UUID,
        expiry_time: int,
        max_sessions: int,
        refresh_token_hash: str,
    ) -> UserSessionModel:
        """Create new session with refresh token.

        Args:
            user_id: User ID.
            expiry_time: Session expiry in minutes.
            max_sessions: Max concurrent sessions (older ones revoked).
            refresh_token_hash: SHA-256 hash of refresh token.

        Returns:
            Created session.
        """
        now = self._utcnow()

        # Revoke excess sessions (keep max_sessions - 1, since we're adding one).
        excess_ids: list[UUID] = [
            sid
            async for sid in UserSessionModel.objects.filter(
                user_id=user_id,
                revoked_at__isnull=True,
            )
            .order_by("-expires_at")
            .values_list("id", flat=True)[max_sessions - 1 :]
        ]
        if excess_ids:
            await UserSessionModel.objects.filter(
                id__in=excess_ids,
            ).aupdate(revoked_at=now)

        session = await UserSessionModel.objects.acreate(
            user_id=user_id,
            expires_at=now + timedelta(minutes=expiry_time),
            refresh_token_hash=refresh_token_hash,
        )
        return session

    async def rotate_refresh_token(
        self,
        session: UserSessionModel,
        new_refresh_token_hash: str,
        expiry_time: int,
    ) -> None:
        """Rotate refresh token and extend session.

        Args:
            session: Existing session to rotate.
            new_refresh_token_hash: New refresh token hash.
            expiry_time: New expiry time in minutes.
        """
        session.refresh_token_hash = new_refresh_token_hash
        session.expires_at = self._utcnow() + timedelta(minutes=expiry_time)
        await session.asave(update_fields=["refresh_token_hash", "expires_at"])

    async def revoke(self, session_id: UUID) -> bool:
        """Revoke session. Returns True if revoked."""
        session = await self.get_session_by_id(session_id)
        if session and session.revoked_at is None:
            session.revoked_at = self._utcnow()
            await session.asave(update_fields=["revoked_at"])
            return True
        return False

    async def revoke_by_refresh_token(self, refresh_token_hash: str) -> bool:
        """Revoke session by refresh token hash.

        Args:
            refresh_token_hash: SHA-256 hash of refresh token.

        Returns:
            True if session was revoked, False otherwise.
        """
        _, session = await self.get_user_valid_session_by_refresh_token(
            refresh_token_hash
        )
        if session:
            session.revoked_at = self._utcnow()
            await session.asave(update_fields=["revoked_at"])
            return True
        return False

    async def delete_expired(self) -> int:
        """Delete revoked/expired sessions. Returns count deleted."""
        now = self._utcnow()
        result = await UserSessionModel.objects.filter(
            Q(revoked_at__isnull=False) | Q(expires_at__lte=now)
        ).adelete()
        return result[0]
