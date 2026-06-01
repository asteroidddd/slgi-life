from __future__ import annotations

from django.db import models


class RegionParkAreaCache(models.Model):
    """Precomputed park intersection area by Seoul/gu/ldong/adong."""

    cache_key = models.CharField(max_length=40, primary_key=True)
    region_type = models.CharField(max_length=10)
    region_code = models.CharField(max_length=20)
    park_count = models.PositiveIntegerField(default=0)
    park_area_m2 = models.FloatField(default=0)
    region_area_m2 = models.FloatField(null=True, blank=True)
    park_area_ratio = models.FloatField(default=0)
    source_version = models.CharField(max_length=40)
    computed_at = models.DateTimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "region_park_area_cache"
        verbose_name = "region park area cache"
        verbose_name_plural = "region park area caches"
        constraints = [
            models.UniqueConstraint(
                fields=["region_type", "region_code"],
                name="uq_region_park_area_cache_region",
            )
        ]
        indexes = [
            models.Index(fields=["region_type"], name="region_park_type_idx"),
            models.Index(fields=["source_version"], name="region_park_source_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.region_type}:{self.region_code}"


class RegionAmenityCategoryCache(models.Model):
    """Precomputed amenity category counts by Seoul/gu/ldong/adong."""

    cache_key = models.CharField(max_length=80, primary_key=True)
    region_type = models.CharField(max_length=10)
    region_code = models.CharField(max_length=20)
    category = models.CharField(max_length=30)
    amenity_count = models.PositiveIntegerField(default=0)
    density_per_km2 = models.FloatField(null=True, blank=True)
    region_area_m2 = models.FloatField(null=True, blank=True)
    source_version = models.CharField(max_length=40)
    computed_at = models.DateTimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "region_amenity_category_cache"
        verbose_name = "region amenity category cache"
        verbose_name_plural = "region amenity category caches"
        constraints = [
            models.UniqueConstraint(
                fields=["region_type", "region_code", "category"],
                name="uq_region_amenity_cache_region_category",
            )
        ]
        indexes = [
            models.Index(fields=["region_type", "category"], name="region_amenity_type_cat_idx"),
            models.Index(fields=["region_code"], name="region_amenity_code_idx"),
            models.Index(fields=["source_version"], name="region_amenity_source_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.region_type}:{self.region_code}:{self.category}"
