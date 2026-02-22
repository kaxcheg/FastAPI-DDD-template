from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories import Repository
from app.infrastructure.db.sqlalchemy.models.user import UserORM
from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM


class UserSessionORMRepo(Repository):
    def __init__(self, db_session: AsyncSession) -> None:
        self._s = db_session

    @staticmethod
    def _utcnow() -> datetime:
        # Always return timezone-aware UTC.
        return datetime.now(timezone.utc)

    async def get_user_if_session_valid(
        self, user_id: UUID, session_id: UUID
    ) -> UserORM | None:
        stmt = (
            select(UserORM)
            .join(UserSessionORM, UserSessionORM.user_id == UserORM.id)
            .where(
                UserORM.id == user_id,
                UserORM.is_active.is_(True),
                UserSessionORM.id == session_id,
                UserSessionORM.is_revoked.is_(False),  # type: ignore[attr-defined]
            )
            .limit(1)
        )

        res = await self._s.execute(stmt)
        return res.scalar_one_or_none()

    async def get_session_by_id(self, session_id: UUID) -> UserSessionORM | None:
        return await self._s.get(UserSessionORM, session_id)

    async def get_user_valid_session_by_refresh_token(
        self, refresh_token_hash: str
    ) -> tuple[UserORM, UserSessionORM] | tuple[None, None]:
        """Find session by refresh token hash (refresh flow).

        Args:
            refresh_token_hash: SHA-256 hash of refresh token.

        Returns:
            UserSessionORM if found and valid, else None.
        """
        stmt = (
            select(UserORM, UserSessionORM)
            .join(UserSessionORM, UserORM.id == UserSessionORM.user_id)
            .where(
                UserORM.is_active.is_(True),
                UserSessionORM.refresh_token_hash == refresh_token_hash,
                UserSessionORM.is_revoked.is_(False),  # type: ignore[attr-defined]
            )
            .limit(1)
        )
        res = await self._s.execute(stmt)

        row = res.one_or_none()

        if row is None:
            return None, None

        user, session = row
        return user, session

    async def create(
        self,
        user_id: UUID,
        expiry_time: int,
        max_sessions: int,
        refresh_token_hash: str,
    ) -> UserSessionORM:
        """Create new session with refresh token.

        Args:
            user_id: User ID.
            expiry_time: Session expiry in minutes.
            max_sessions: Max concurrent sessions (older ones revoked).
            refresh_token_hash: SHA-256 hash of refresh token.

        Returns:
            UserSessionORM: Created session.
        """
        existing_sessions = await self._s.execute(
            select(UserSessionORM)
            .where(
                UserSessionORM.user_id == user_id,
                UserSessionORM.is_revoked.is_(False),  # type: ignore[attr-defined]
            )
            .order_by(UserSessionORM.expires_at.desc())
            .offset(max_sessions - 1)
        )
        for old_session in existing_sessions.scalars():
            old_session.revoked_at = self._utcnow()

        user_session = UserSessionORM(
            user_id=user_id,
            expires_at=timedelta(minutes=expiry_time) + self._utcnow(),
            refresh_token_hash=refresh_token_hash,
        )
        self._s.add(user_session)
        await self._s.flush()

        return user_session

    async def rotate_refresh_token(
        self,
        session: UserSessionORM,
        new_refresh_token_hash: str,
        expiry_time: int,
    ) -> None:
        """Rotate refresh token and extend session.

        This implements one-time use refresh tokens for security.

        Args:
            session: Existing session to rotate.
            new_refresh_token_hash: New refresh token hash.
            expiry_time: New expiry time in minutes.
        """
        session.refresh_token_hash = new_refresh_token_hash
        session.expires_at = timedelta(minutes=expiry_time) + self._utcnow()
        await self._s.flush()

    async def revoke(self, session_id: UUID) -> bool:
        """Revoke session. Returns True if revoked."""
        user_session = await self.get_session_by_id(session_id)
        if user_session and user_session.revoked_at is None:
            user_session.revoked_at = self._utcnow()
            await self._s.flush()
            return True
        return False

    async def revoke_by_refresh_token(self, refresh_token_hash: str) -> bool:
        """Revoke session by refresh token hash.

        Used when detecting refresh token reuse (security incident).

        Args:
            refresh_token_hash: SHA-256 hash of refresh token.

        Returns:
            bool: True if session was revoked, False otherwise.
        """
        _, session = await self.get_user_valid_session_by_refresh_token(
            refresh_token_hash
        )
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            await self._s.flush()
            return True
        return False

    async def delete_expired(self) -> int:
        result = await self._s.execute(
            delete(UserSessionORM).where(UserSessionORM.is_revoked)
        )
        return result.rowcount
