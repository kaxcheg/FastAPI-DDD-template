from datetime import datetime
import uuid
from sqlalchemy import String, LargeBinary, Enum as SAEnum, Boolean, UniqueConstraint, CheckConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID


from app.domain.value_objects import UserRole
from app.domain.value_objects.constants import HASH_LEN, USERNAME_MAX_LEN, USERNAME_MIN_LEN

from app.infrastructure.db.sqlalchemy.models.base import Base

# Define the users table
class UserORM(Base):
    __tablename__ = "users"
    
    # Primary key: UUID as 36-char string
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False, )
    # Unique username (max length defined by domain constant)
    username: Mapped[str] = mapped_column(String(USERNAME_MAX_LEN), unique=True, nullable=False)

    # Password hash bytes (fixed length defined by domain constant)
    password_hash: Mapped[bytes] = mapped_column(LargeBinary(HASH_LEN), nullable=False)

    # Enum for user role (e.g. admin, user)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)

    # Active flag
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Explicitly name the uniqueness constraint for easier migration/management
    __table_args__ = (
        UniqueConstraint("username", name="uq_user_username"),
        CheckConstraint(f"length(username) >= {USERNAME_MIN_LEN}", name="username_min_length"),
    )