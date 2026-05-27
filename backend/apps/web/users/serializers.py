from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Favorite, User


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    school = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=80)
    year = serializers.IntegerField(required=False, allow_null=True)
    nickname = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=30)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)

    def validate_username(self, value: str) -> str:
        username = value.strip()
        if not username:
            raise serializers.ValidationError("username is required.")
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError("username already exists.")
        return username

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class MeSerializer(serializers.ModelSerializer):
    home_lat = serializers.SerializerMethodField()
    home_lng = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "nickname",
            "school",
            "year",
            "address",
            "home_lat",
            "home_lng",
            "address_geocode_status",
            "address_geocode_error",
        )

    def get_home_lat(self, obj: User) -> float | None:
        return obj.home_location.y if obj.home_location else None

    def get_home_lng(self, obj: User) -> float | None:
        return obj.home_location.x if obj.home_location else None


class MePatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("school", "year", "nickname", "address")
        extra_kwargs = {
            "school": {"required": False, "allow_blank": True},
            "year": {"required": False, "allow_null": True},
            "nickname": {"required": False, "allow_blank": True},
            "address": {"required": False, "allow_blank": True},
        }


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
