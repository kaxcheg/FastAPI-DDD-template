"""URL configuration for Django DRF interface."""

from __future__ import annotations

from django.http import JsonResponse
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from app.interface.drf.views.auth import LoginView, LogoutView, RefreshView
from app.interface.drf.views.users import (
    ChangePasswordView,
    UserDetailView,
    UserListView,
)


async def health_check(request: object) -> JsonResponse:
    """Return simple health status."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health", health_check),
    # OpenAPI / docs
    path("openapi.json", SpectacularAPIView.as_view(), name="schema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Auth
    path("auth/login", LoginView.as_view()),
    path("auth/refresh", RefreshView.as_view()),
    path("auth/logout", LogoutView.as_view()),
    # Users
    path("users", UserListView.as_view()),
    path("users/<uuid:user_id>", UserDetailView.as_view()),
    path("users/<uuid:user_id>/password", ChangePasswordView.as_view()),
]
