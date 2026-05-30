from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.profile.validators import validate_school_name
from apps.accounts.user.models import User


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    school = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=80)
    year = serializers.IntegerField(required=False, allow_null=True)
    nickname = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=30)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    terms_agreed = serializers.BooleanField(write_only=True)

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

    def validate_terms_agreed(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("terms agreement is required.")
        return value

    def validate_school(self, value: str | None) -> str:
        return validate_school_name(value)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
