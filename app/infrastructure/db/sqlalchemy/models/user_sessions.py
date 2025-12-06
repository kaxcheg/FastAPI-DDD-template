import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, func, or_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.sqlalchemy.models.base import Base


class UserSessionORM(Base):
    __tablename__ = "user_sessions"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_token_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    @hybrid_property
    def is_revoked(self) -> bool:  # type: ignore[no-redef]
        if self.revoked_at is not None:
            return True
        return self.expires_at <= datetime.now(timezone.utc)

    @is_revoked.expression  # type: ignore[no-redef]
    def is_revoked(cls):  # type: ignore[no-redef]
        return or_(cls.revoked_at.isnot(None), cls.expires_at <= func.now())  # type: ignore[attr-defined]
