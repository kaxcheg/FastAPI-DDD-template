from __future__ import annotations

import uuid

from django.db import models
from django.db.models import CharField
from django.db.models.functions import Length

from app.domain.value_objects import UserRole
from app.domain.value_objects.constants import (
    HASH_LEN,
    USERNAME_MAX_LEN,
    USERNAME_MIN_LEN,
)

# Register Length as a lookup transform so we can use username__length in Q().
CharField.register_lookup(Length)


class UserModel(models.Model):
    """Django ORM model for the users table (mirrors SQLAlchemy UserORM)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=USERNAME_MAX_LEN, unique=True)
    password_hash = models.BinaryField(max_length=HASH_LEN)
    role = models.CharField(
        max_length=10,
        choices=[(r.value, r.value) for r in UserRole],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        constraints = [
            models.UniqueConstraint(fields=["username"], name="uq_user_username"),
            models.CheckConstraint(
                condition=models.Q(username__length__gte=USERNAME_MIN_LEN),
                name="username_min_length",
            ),
        ]
