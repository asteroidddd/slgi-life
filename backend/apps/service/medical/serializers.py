from __future__ import annotations

from rest_framework import serializers

from apps.public_data.medical.models import (
    MedicalEmergency,
    MedicalFacility,
    MedicalFacilityHours,
    MedicalFacilitySpecialty,
    MedicalHiraMapping,
    MedicalHolidayCare,
)


class MedicalFacilityListSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    is_emergency = serializers.SerializerMethodField()
    distance_m = serializers.SerializerMethodField()

    class Meta:
        model = MedicalFacility
        fields = (
            "hpid",
            "category",
            "type",
            "name",
            "address",
            "tel1",
            "lat",
            "lng",
            "is_emergency",
            "distance_m",
        )

    def get_category(self, obj: MedicalFacility) -> str:
        return self.context["category_for"](obj)

    def get_lat(self, obj: MedicalFacility) -> float | None:
        return obj.location.y if obj.location else None

    def get_lng(self, obj: MedicalFacility) -> float | None:
        return obj.location.x if obj.location else None

    def get_is_emergency(self, obj: MedicalFacility) -> bool:
        if hasattr(obj, "has_emergency"):
            return bool(obj.has_emergency)
        try:
            return bool(obj.emergency)
        except MedicalEmergency.DoesNotExist:
            return False

    def get_distance_m(self, obj: MedicalFacility) -> float | None:
        distance = getattr(obj, "distance", None)
        if distance is None:
            return None
        return round(float(distance.m), 1)


class MedicalFacilityHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalFacilityHours
        fields = ("day_type", "open_time", "close_time", "is_closed")


class MedicalEmergencySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalEmergency
        fields = ("phpid", "emergency_type", "tel2", "has_emergency_room", "note")


class MedicalHolidayCareSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHolidayCare
        fields = ("care_date", "open_time", "close_time", "is_closed", "note")


class MedicalFacilitySpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalFacilitySpecialty
        fields = ("specialty_name", "specialty_group", "specialist_count")


class MedicalFacilityDetailSerializer(MedicalFacilityListSerializer):
    hours = MedicalFacilityHoursSerializer(many=True, read_only=True)
    emergency = MedicalEmergencySerializer(read_only=True)
    holiday_cares = MedicalHolidayCareSerializer(many=True, read_only=True)
    specialties = serializers.SerializerMethodField()
    note = serializers.CharField()

    def get_specialties(self, obj: MedicalFacility) -> list[dict]:
        try:
            mapping = obj.hira_mapping
        except MedicalHiraMapping.DoesNotExist:
            return []
        return MedicalFacilitySpecialtySerializer(mapping.specialties.all(), many=True).data

    class Meta(MedicalFacilityListSerializer.Meta):
        fields = MedicalFacilityListSerializer.Meta.fields + (
            "note",
            "hours",
            "emergency",
            "holiday_cares",
            "specialties",
        )
