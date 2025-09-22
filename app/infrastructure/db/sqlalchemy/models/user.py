import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import LargeBinary, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.value_objects import UserRole
from app.domain.value_objects.constants import (
    HASH_LEN,
    USERNAME_MAX_LEN,
    USERNAME_MIN_LEN,
)
from app.infrastructure.db.sqlalchemy.models.base import Base


class UserORM(Base):
    __tablename__ = "users"

    # Primary key: UUID as 36-char string
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    username: Mapped[str] = mapped_column(
        String(USERNAME_MAX_LEN), unique=True, nullable=False
    )
    password_hash: Mapped[bytes] = mapped_column(LargeBinary(HASH_LEN), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Explicitly name the uniqueness constraint for easier migration/management
    __table_args__ = (
        UniqueConstraint("username", name="uq_user_username"),
        CheckConstraint(
            f"length(username) >= {USERNAME_MIN_LEN}", name="username_min_length"
        ),
    )
