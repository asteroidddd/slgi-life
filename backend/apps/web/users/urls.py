"""
users 앱 URL.

마운트: config/urls.py 의 path("api/", include("apps.web.users.urls"))
즉 최종 경로는 /api/auth/* , /api/users/me, /api/users/me/* 등.
"""

from django.urls import path

from .views import (
    FavoriteDetailView,
    FavoritesView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)

app_name = "users"

urlpatterns = [
    # 인증 (CSRF 면제)
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    # 마이페이지
    path("users/me", MeView.as_view(), name="me"),
    path(
        "users/me/favorites",
        FavoritesView.as_view(),
        name="me-favorites",
    ),
    path(
        "users/me/favorites/<str:slug>",
        FavoriteDetailView.as_view(),
        name="me-favorite-detail",
    ),
]
