from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.sqlalchemy.models.user import UserORM
from app.infrastructure.db.sqlalchemy.models.user_sessions import UserSessionORM


class UserSessionService:
    def __init__(self, db_session: AsyncSession, expiry_time) -> None:
        self._s = db_session
        self._expiry_time = expiry_time

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
        result = await self._s.execute(
            select(UserSessionORM).where(UserSessionORM.id == session_id)
        )
        return result.scalars().first()

    async def create(self, user_id: UUID) -> UserSessionORM:
        user_session = UserSessionORM(
            user_id=user_id,
            expires_at=timedelta(minutes=self._expiry_time)
            + datetime.now(timezone.utc),
        )
        self._s.add(user_session)
        await self._s.flush()

        return user_session

    def check_exp(self, user_session: UserSessionORM) -> bool:
        return user_session.expires_at < datetime.now(timezone.utc)
