"""Django settings for the DRF interface stack."""

from __future__ import annotations

from app.config import get_settings

cfg = get_settings()

SECRET_KEY = cfg.JWT_SECRET.get_secret_value()
DEBUG = cfg.DEBUG
ALLOWED_HOSTS: list[str] = ["*"]

INSTALLED_APPS: list[str] = [
    "django.contrib.contenttypes",
    "rest_framework",
    "drf_spectacular",
    "app.infrastructure.db.django_orm",
]

MIDDLEWARE: list[str] = [
    "app.interface.drf.middleware.ExceptionHandlerMiddleware",
    "app.interface.drf.middleware.CacheControlMiddleware",
    "app.interface.drf.middleware.AuthMiddleware",
]

ROOT_URLCONF = "app.interface.drf.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
    },
]

DATABASES: dict[str, dict[str, object]] = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": cfg.DB_PATH,
        "USER": cfg.DB_USER,
        "PASSWORD": cfg.DB_USER_SECRET.get_secret_value(),
        "HOST": cfg.DB_HOST,
        "PORT": cfg.DB_PORT,
        "OPTIONS": {"options": f"-c search_path={cfg.DB_TABLE_SCHEMA},public"},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK: dict[str, object] = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
}

SPECTACULAR_SETTINGS: dict[str, object] = {
    "TITLE": "dddapitpl",
    "VERSION": "0.0.1",
    "SERVE_INCLUDE_SCHEMA": False,
    "SECURITY": [{"BearerAuth": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
}

USE_TZ = True

LOGGING_CONFIG = None  # App uses its own logging via app.config.logging.
