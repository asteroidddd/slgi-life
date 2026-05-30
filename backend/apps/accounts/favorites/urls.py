from django.urls import path

from apps.accounts.favorites.views import FavoriteDetailView, FavoritesView

urlpatterns = [
    path("users/me/favorites", FavoritesView.as_view(), name="me-favorites"),
    path("users/me/favorites/<str:slug>", FavoriteDetailView.as_view(), name="me-favorite-detail"),
]
