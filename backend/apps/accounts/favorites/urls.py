from django.urls import path

from apps.accounts.favorites.views import (
    CandidateRegionsView,
    FavoriteDetailView,
    FavoritesView,
    RecommendationConditionsView,
)

urlpatterns = [
    path("users/me/favorites", FavoritesView.as_view(), name="me-favorites"),
    path("users/me/favorites/<str:slug>", FavoriteDetailView.as_view(), name="me-favorite-detail"),
    path("users/me/candidate-regions", CandidateRegionsView.as_view(), name="me-candidate-regions"),
    path("users/me/recommendation-conditions", RecommendationConditionsView.as_view(), name="me-recommendation-conditions"),
]
