"""DRF serializers (equivalent to FastAPI Pydantic schemas)."""

from __future__ import annotations

from rest_framework import serializers

from app.domain.value_objects.constants import (
    RAW_PASSWORD_MAX_LEN,
    RAW_PASSWORD_MIN_LEN,
    USERNAME_MAX_LEN,
    USERNAME_MIN_LEN,
)


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class CreateUserRequestSerializer(serializers.Serializer):
    username = serializers.CharField(
        min_length=USERNAME_MIN_LEN, max_length=USERNAME_MAX_LEN
    )
    password = serializers.CharField(
        min_length=RAW_PASSWORD_MIN_LEN, max_length=RAW_PASSWORD_MAX_LEN
    )
    role = serializers.CharField()


class UserResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()


class CreateUserResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()
    role = serializers.CharField()


class GetAllUsersResponseSerializer(serializers.Serializer):
    users = UserResponseSerializer(many=True)


class GetUserResponseSerializer(serializers.Serializer):
    user = UserResponseSerializer()


class UpdateUserRequestSerializer(serializers.Serializer):
    username = serializers.CharField(
        min_length=USERNAME_MIN_LEN,
        max_length=USERNAME_MAX_LEN,
        required=False,
        default=None,
        allow_null=True,
    )
    role = serializers.CharField(required=False, default=None, allow_null=True)


class UpdateUserResponseSerializer(serializers.Serializer):
    user = UserResponseSerializer()


class ChangePasswordRequestSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        min_length=RAW_PASSWORD_MIN_LEN, max_length=RAW_PASSWORD_MAX_LEN
    )


class ChangePasswordResponseSerializer(serializers.Serializer):
    user = UserResponseSerializer()


class DeleteUserResponseSerializer(serializers.Serializer):
    user = UserResponseSerializer()


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class TokenSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    access_token_type = serializers.CharField()
    expires_in = serializers.IntegerField()
    refresh_token = serializers.CharField(allow_null=True)
    refresh_expires_in = serializers.IntegerField()


class RefreshTokenRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()
