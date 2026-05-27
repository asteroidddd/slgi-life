from django.db import models


class ScoreRangeMixin(models.Model):
    score_rent = models.FloatField(null=True, blank=True)
    score_amenity = models.FloatField()
    score_transit = models.FloatField()
    score_safety = models.FloatField(default=0.0)
    score_total = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class RankedScoreMixin(ScoreRangeMixin):
    rank_rent = models.PositiveIntegerField(null=True, blank=True)
    rank_amenity = models.PositiveIntegerField(null=True, blank=True)
    rank_transit = models.PositiveIntegerField(null=True, blank=True)
    rank_safety = models.PositiveIntegerField(null=True, blank=True)
    rank_total = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        abstract = True


class CurrentSeoul(ScoreRangeMixin):
    seoul = models.OneToOneField(
        "regions.Seoul",
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="code",
        related_name="current_score",
    )

    class Meta:
        db_table = "current_seoul"


class CurrentGu(RankedScoreMixin):
    gu = models.OneToOneField(
        "regions.Gu",
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="gu_code",
        related_name="current_score",
    )

    class Meta:
        db_table = "current_gu"


class CurrentLdong(RankedScoreMixin):
    ldong = models.OneToOneField(
        "regions.Ldong",
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="ldong_code",
        related_name="current_score",
    )

    class Meta:
        db_table = "current_ldong"


class CurrentAdong(RankedScoreMixin):
    adong = models.OneToOneField(
        "regions.Adong",
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="adong_code",
        related_name="current_score",
    )

    class Meta:
        db_table = "current_adong"
