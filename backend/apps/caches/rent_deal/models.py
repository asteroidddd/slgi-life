from __future__ import annotations

from django.db import models


class RentDealGeocodeCache(models.Model):
    """Persistent address-to-coordinate cache for rent_deal ingestion."""

    cache_key = models.CharField(max_length=64, primary_key=True)
    normalized_query = models.CharField(max_length=255, unique=True)
    gu_code = models.CharField(max_length=20, null=True, blank=True)
    ldong_code = models.CharField(max_length=20, null=True, blank=True)
    jibun = models.CharField(max_length=50, null=True, blank=True)
    provider = models.CharField(max_length=30, default="imported")
    status = models.CharField(max_length=20)
    lng = models.FloatField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    adong_code = models.CharField(max_length=20, null=True, blank=True)
    error = models.CharField(max_length=255, null=True, blank=True)
    hit_count = models.PositiveIntegerField(default=0)
    first_seen_at = models.DateTimeField()
    last_used_at = models.DateTimeField()
    fetched_at = models.DateTimeField(null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "rent_deal_geocode_cache"
        verbose_name = "rent deal geocode cache"
        verbose_name_plural = "rent deal geocode caches"
        indexes = [
            models.Index(fields=["ldong_code", "jibun"], name="rent_geo_ldong_jibun_idx"),
            models.Index(fields=["status"], name="rent_geo_status_idx"),
            models.Index(fields=["provider"], name="rent_geo_provider_idx"),
            models.Index(fields=["adong_code"], name="rent_geo_adong_idx"),
            models.Index(fields=["last_used_at"], name="rent_geo_last_used_idx"),
        ]

    @property
    def lng_lat(self) -> list[float] | None:
        if self.lng is None or self.lat is None:
            return None
        return [self.lng, self.lat]

    def __str__(self) -> str:
        return f"{self.normalized_query} [{self.status}]"
