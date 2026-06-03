from django.conf import settings
from django.db import models


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="favorites",
        on_delete=models.CASCADE,
    )
    adong = models.ForeignKey(
        "regions.Adong",
        related_name="favorited_by",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_favorite"
        verbose_name = "찜한 동네"
        verbose_name_plural = "찜한 동네"
        unique_together = ("user", "adong")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="user_favori_user_id_9351bd_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} ♡ {self.adong}"


class CandidateRegion(models.Model):
    class RegionLevel(models.TextChoices):
        ADONG = "adong", "행정동"
        LDONG = "ldong", "법정동"

    class Source(models.TextChoices):
        CONDITIONS = "conditions", "추천"
        MAP = "map", "지도"
        DETAIL = "detail", "동네 정보"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="candidate_regions",
        on_delete=models.CASCADE,
    )
    region_level = models.CharField(max_length=8, choices=RegionLevel.choices)
    slug = models.CharField(max_length=160)
    code = models.CharField(max_length=40, blank=True)
    gu = models.CharField(max_length=80)
    name = models.CharField(max_length=80)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    score_rent = models.FloatField(null=True, blank=True)
    score_transit = models.FloatField(null=True, blank=True)
    score_amenity = models.FloatField(null=True, blank=True)
    score_safety = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.MAP)
    added_at_ms = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_candidate_region"
        verbose_name = "담은 동네"
        verbose_name_plural = "담은 동네"
        constraints = [
            models.UniqueConstraint(fields=["user", "region_level", "slug"], name="uniq_user_candidate_region"),
        ]
        ordering = ["-added_at_ms", "-updated_at"]
        indexes = [
            models.Index(fields=["user", "-added_at_ms"], name="user_cand_user_id_4efc_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.gu} {self.name}"
