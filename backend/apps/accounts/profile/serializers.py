from __future__ import annotations

from rest_framework import serializers

from apps.accounts.profile.models import get_user_profile
from apps.accounts.profile.validators import validate_school_name
from apps.accounts.social.models import SocialAccount
from apps.accounts.user.models import User


class MeSerializer(serializers.ModelSerializer):
    home_lat = serializers.SerializerMethodField()
    home_lng = serializers.SerializerMethodField()
    auth_provider = serializers.SerializerMethodField()
    nickname = serializers.SerializerMethodField()
    school = serializers.SerializerMethodField()
    year = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    address_geocode_status = serializers.SerializerMethodField()
    address_geocode_error = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "auth_provider",
            "nickname",
            "school",
            "year",
            "address",
            "home_lat",
            "home_lng",
            "address_geocode_status",
            "address_geocode_error",
        )

    def _profile(self, obj: User):
        return get_user_profile(obj)

    def get_auth_provider(self, obj: User) -> str:
        if obj.social_accounts.filter(provider=SocialAccount.PROVIDER_KAKAO).exists():
            return SocialAccount.PROVIDER_KAKAO
        return "password"

    def get_nickname(self, obj: User) -> str:
        return self._profile(obj).nickname

    def get_school(self, obj: User) -> str:
        return self._profile(obj).school

    def get_year(self, obj: User) -> int | None:
        return self._profile(obj).year

    def get_address(self, obj: User) -> str:
        return self._profile(obj).address

    def get_home_lat(self, obj: User) -> float | None:
        location = self._profile(obj).home_location
        return location.y if location else None

    def get_home_lng(self, obj: User) -> float | None:
        location = self._profile(obj).home_location
        return location.x if location else None

    def get_address_geocode_status(self, obj: User) -> str:
        return self._profile(obj).address_geocode_status

    def get_address_geocode_error(self, obj: User) -> str:
        return self._profile(obj).address_geocode_error


class MePatchSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=False)
    school = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=80)
    year = serializers.IntegerField(required=False, allow_null=True)
    nickname = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=30)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)

    def validate_school(self, value: str | None) -> str:
        return validate_school_name(value)

    def update(self, instance: User, validated_data: dict) -> User:
        if "email" in validated_data:
            instance.email = validated_data["email"]
            instance.save(update_fields=["email"])

        profile = get_user_profile(instance)
        profile_fields = {"school", "year", "nickname", "address"} & set(validated_data)
        for field in profile_fields:
            value = validated_data[field]
            if value is None and field != "year":
                value = ""
            setattr(profile, field, value)
        if profile_fields:
            profile.save(update_fields=sorted(profile_fields))
        return instance

    def create(self, validated_data: dict) -> User:
        raise NotImplementedError
