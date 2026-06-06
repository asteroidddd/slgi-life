from django.db import models


class AdongUnivTime(models.Model):
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.CASCADE,
        db_column="adong_code",
        related_name="univ_times",
    )
    univ = models.ForeignKey(
        "univ.Univ",
        on_delete=models.CASCADE,
        db_column="univ_code",
        related_name="adong_times",
    )
    time = models.PositiveIntegerField(help_text="대학까지 예상 소요 시간(분)")

    class Meta:
        db_table = "adong_univ_time"
        verbose_name = "행정동-대학 시간"
        verbose_name_plural = "행정동-대학 시간"
        constraints = [
            models.UniqueConstraint(fields=["adong", "univ"], name="uq_adong_univ_time"),
        ]
        indexes = [
            models.Index(fields=["univ", "time"], name="adong_univ_time_univ_idx"),
            models.Index(fields=["adong"], name="adong_univ_time_adong_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.adong_id} {self.univ_id} {self.time}분"


class LdongUnivTime(models.Model):
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.CASCADE,
        db_column="ldong_code",
        related_name="univ_times",
    )
    univ = models.ForeignKey(
        "univ.Univ",
        on_delete=models.CASCADE,
        db_column="univ_code",
        related_name="ldong_times",
    )
    time = models.PositiveIntegerField(help_text="대학까지 예상 소요 시간(분)")

    class Meta:
        db_table = "ldong_univ_time"
        verbose_name = "법정동-대학 시간"
        verbose_name_plural = "법정동-대학 시간"
        constraints = [
            models.UniqueConstraint(fields=["ldong", "univ"], name="uq_ldong_univ_time"),
        ]
        indexes = [
            models.Index(fields=["univ", "time"], name="ldong_univ_time_univ_idx"),
            models.Index(fields=["ldong"], name="ldong_univ_time_ldong_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.ldong_id} {self.univ_id} {self.time}분"



class RecommendRentRegionCache(models.Model):
    cache_key = models.CharField(max_length=120, primary_key=True)
    region_type = models.CharField(max_length=10)
    region_code = models.CharField(max_length=20)
    scope = models.CharField(max_length=20, default="recent_365d")
    as_of_date = models.DateField()
    recent_from = models.DateField()
    conversion_rate_period = models.CharField(max_length=20, blank=True, default="")
    monthly_rate = models.FloatField()
    deal_count = models.PositiveIntegerField(default=0)
    avg_per_m2 = models.FloatField(null=True, blank=True)
    median_converted = models.FloatField(null=True, blank=True)
    min_contract_date = models.DateField(null=True, blank=True)
    max_contract_date = models.DateField(null=True, blank=True)
    source_version = models.CharField(max_length=40, blank=True, default="")
    computed_at = models.DateTimeField()

    class Meta:
        db_table = "recommend_rent_region_cache"
        verbose_name = "recommend rent region cache"
        verbose_name_plural = "recommend rent region caches"
        constraints = [
            models.UniqueConstraint(
                fields=["region_type", "region_code", "scope", "as_of_date", "conversion_rate_period"],
                name="uq_recommend_rent_region_cache",
            )
        ]
        indexes = [
            models.Index(fields=["region_type", "scope", "as_of_date"], name="recommend_rent_scope_idx"),
            models.Index(fields=["region_type", "region_code"], name="recommend_rent_region_idx"),
            models.Index(fields=["source_version"], name="recommend_rent_source_idx"),
        ]

    def __str__(self) -> str:
        return self.cache_key
