from __future__ import annotations

from rest_framework import serializers

from apps.accounts.favorites.models import Favorite


class FavoriteItemSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    gu = serializers.CharField()
    score = serializers.FloatField()
    created_at = serializers.DateTimeField()


def build_favorite_item(fav: Favorite, weights: dict[str, float] | None = None) -> dict:
    adong = fav.adong
    current = getattr(adong, "current_score", None)
    score = float(getattr(current, "score_total", 0.0) or 0.0)
    return {
        "slug": adong.slug,
        "name": adong.name,
        "gu": adong.gu.name,
        "score": round(score, 2),
        "created_at": fav.created_at,
    }
