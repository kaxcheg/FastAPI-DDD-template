from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select,delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.sqlalchemy.models.user import UserORM
from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM


class UserSessionORMRepo:
    def __init__(self, db_session: AsyncSession) -> None:
        self._s = db_session

    async def get_user_if_session_valid(
        self, user_id: UUID, session_id: UUID
    ) -> UserORM | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(UserORM)
            .join(UserSessionORM, UserSessionORM.user_id == UserORM.id)
            .where(
                UserORM.id == user_id,
                UserSessionORM.id == session_id,
                UserSessionORM.revoked_at.is_(None),
                UserSessionORM.expires_at > now,
            )
            .limit(1)
        )

        res = await self._s.execute(stmt)
        return res.scalar_one_or_none()

    async def get_session_by_id(self, session_id: UUID) -> UserSessionORM | None:
        return await self._s.get(UserSessionORM, session_id)
        
    async def create(self, user_id: UUID, expiry_time: int, max_sessions: int) -> UserSessionORM:
        existing = await self._s.execute(
        select(UserSessionORM)
        .where(UserSessionORM.user_id == user_id, UserSessionORM.revoked_at.is_(None))
        .order_by(UserSessionORM.expires_at.desc())
        .offset(max_sessions - 1)
    )
        for old_session in existing.scalars():
            old_session.revoked_at = datetime.now(timezone.utc)
        
        user_session = UserSessionORM(
            user_id=user_id,
            expires_at=timedelta(minutes=expiry_time)
            + datetime.now(timezone.utc),
        )
        self._s.add(user_session)
        await self._s.flush()

        return user_session

    async def revoke(self, session_id: UUID) -> bool:
        """Revoke session. Returns True if revoked."""
        user_session = await self.get_session_by_id(session_id)
        if user_session and user_session.revoked_at is None:
            user_session.revoked_at = datetime.now(timezone.utc)
            return True
        return False
    
    
    async def delete_expired(self) -> int:
        result = await self._s.execute(
            delete(UserSessionORM).where(
                or_(
                    UserSessionORM.expires_at < datetime.now(timezone.utc),
                    UserSessionORM.revoked_at.isnot(None)
                )
            )
        )
        return result.rowcount