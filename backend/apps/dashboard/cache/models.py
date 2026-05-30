from django.db import models


class DashboardAdongCache(models.Model):
    adong = models.OneToOneField(
        "regions.Adong",
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="dashboard_cache",
        db_column="adong_code",
    )
    region_payload = models.JSONField(default=dict)
    intro = models.TextField(blank=True, default="")
    rent_summary = models.JSONField(default=dict)
    transit_summary = models.JSONField(default=dict)
    infra_summary = models.JSONField(default=dict)
    safety_summary = models.JSONField(default=dict)
    dashboard_payload = models.JSONField(default=dict)
    source_version = models.CharField(max_length=40, blank=True, default="")
    computed_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboard_adong_cache"
        verbose_name = "dashboard adong cache"
        verbose_name_plural = "dashboard adong caches"

    def __str__(self) -> str:
        return self.adong_id


class DashboardLdongCache(models.Model):
    ldong = models.OneToOneField(
        "regions.Ldong",
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="dashboard_cache",
        db_column="ldong_code",
    )
    region_payload = models.JSONField(default=dict)
    intro = models.TextField(blank=True, default="")
    rent_summary = models.JSONField(default=dict)
    transit_summary = models.JSONField(default=dict)
    infra_summary = models.JSONField(default=dict)
    safety_summary = models.JSONField(default=dict)
    dashboard_payload = models.JSONField(default=dict)
    source_version = models.CharField(max_length=40, blank=True, default="")
    computed_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboard_ldong_cache"
        verbose_name = "dashboard ldong cache"
        verbose_name_plural = "dashboard ldong caches"

    def __str__(self) -> str:
        return self.ldong_id

