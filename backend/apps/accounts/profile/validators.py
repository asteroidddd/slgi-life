from rest_framework import serializers

from apps.public_data.univ.models import Univ


def validate_school_name(value: str | None) -> str:
    school = (value or "").strip()
    if not school:
        return ""
    if not Univ.objects.filter(name=school).exists():
        raise serializers.ValidationError("known university name is required.")
    return school
