from __future__ import annotations

from django.contrib.gis.db import models as gis_models
from django.db import models


class MapAmenityMarkerCache(models.Model):
    """Lightweight amenity markers for bbox map rendering."""

    id = models.BigIntegerField(primary_key=True)
    category = models.CharField(max_length=30)
    name = models.CharField(max_length=200)
    location = gis_models.PointField(srid=4326)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "map_amenity_marker_cache"
        verbose_name = "map amenity marker cache"
        verbose_name_plural = "map amenity marker caches"
        indexes = [
            models.Index(fields=["category", "name"], name="map_amenity_cat_name_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.category}:{self.name}"


class MapMedicalMarkerCache(models.Model):
    """Lightweight medical markers for bbox map rendering."""

    hpid = models.CharField(max_length=20, primary_key=True)
    category = models.CharField(max_length=20)
    type = models.CharField(max_length=30)
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=255, blank=True, default="")
    tel1 = models.CharField(max_length=50, blank=True, default="")
    location = gis_models.PointField(srid=4326)
    is_emergency = models.BooleanField(default=False)
    hours_summary = models.JSONField(default=dict)
    specialty_groups = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "map_medical_marker_cache"
        verbose_name = "map medical marker cache"
        verbose_name_plural = "map medical marker caches"
        indexes = [
            models.Index(fields=["category", "name"], name="map_medical_cat_name_idx"),
            models.Index(fields=["is_emergency"], name="map_medical_emergency_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.category}:{self.name}"
