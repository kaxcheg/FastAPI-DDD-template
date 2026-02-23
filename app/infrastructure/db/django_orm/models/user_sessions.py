from __future__ import annotations

import uuid
from datetime import datetime, timezone

from django.db import models


class UserSessionModel(models.Model):
    """Django ORM model for the user_sessions table (mirrors SQLAlchemy UserSessionORM)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "django_orm.UserModel",
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="sessions",
    )
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, default=None)
    refresh_token_hash = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_sessions"

    @property
    def is_revoked(self) -> bool:
        """Session is revoked if explicitly revoked or expired."""
        if self.revoked_at is not None:
            return True
        return self.expires_at <= datetime.now(timezone.utc)
