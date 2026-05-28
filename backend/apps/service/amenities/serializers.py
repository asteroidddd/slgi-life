from __future__ import annotations

from rest_framework import serializers

from .models import Amenity


class AmenityBboxSerializer(serializers.ModelSerializer):
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    class Meta:
        model = Amenity
        fields = ("id", "category", "name", "lat", "lng", "source_table", "source_id")

    def get_lat(self, obj: Amenity) -> float | None:
        return obj.location.y if obj.location else None

    def get_lng(self, obj: Amenity) -> float | None:
        return obj.location.x if obj.location else None
