"""
Current* 4 모델 — sub-plan 2K 신설 (schema.dbml line 407~441 정합).

단위(seoul / gu / ldong / adong)별 최신 score 3종(rent / amenity / transit) 캐시.
- score_rent: 최근 1년 환산월세/㎡ 기반. 거래 0 단위는 NULL.
- score_amenity: 생활/의료/공원 가중합 0~100 (NOT NULL).
- score_transit: 지하철 1km anchor + 버스 면적당 밀도 p95 가중합 0~100 (NOT NULL).

CHECK 제약 (DECISIONS O 섹션 lock):
- score_amenity / score_transit: [0, 100]
- score_rent: [0, 100] 또는 NULL
"""

from django.db import models
from django.db.models import Q


class CurrentSeoul(models.Model):
    """서울시 1행 최신 score 캐시. RDS `current_seoul` 테이블."""

    seoul = models.OneToOneField(
        "regions.Seoul",
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="code",
        related_name="current_score",
        help_text="서울시 코드 (RDS current_seoul.code)",
    )
    score_rent = models.FloatField(
        null=True,
        blank=True,
        help_text="최근 1년 환산월세/㎡ 기반 score. 거래 0 단위는 NULL",
    )
    score_amenity = models.FloatField(
        help_text="생활/의료/공원 가중합 0~100",
    )
    score_transit = models.FloatField(
        help_text="지하철 1km anchor + 버스 면적당 밀도 p95 가중합 0~100",
    )

    class Meta:
        db_table = "current_seoul"
        verbose_name = "서울 최신 score"
        verbose_name_plural = "서울 최신 score"
        constraints = [
            models.CheckConstraint(
                check=Q(score_amenity__gte=0, score_amenity__lte=100),
                name="ck_current_seoul_amenity",
            ),
            models.CheckConstraint(
                check=Q(score_transit__gte=0, score_transit__lte=100),
                name="ck_current_seoul_transit",
            ),
            models.CheckConstraint(
                check=Q(score_rent__gte=0, score_rent__lte=100) | Q(score_rent__isnull=True),
                name="ck_current_seoul_rent",
            ),
        ]


class CurrentGu(models.Model):
    """자치구 25개 최신 score 캐시. RDS `current_gu` 테이블."""

    gu = models.OneToOneField(
        "regions.Gu",
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="gu_code",
        related_name="current_score",
        help_text="자치구 코드 (RDS current_gu.gu_code)",
    )
    score_rent = models.FloatField(
        null=True,
        blank=True,
        help_text="최근 1년 환산월세/㎡ 기반 score. 거래 0 단위는 NULL",
    )
    score_amenity = models.FloatField(
        help_text="생활/의료/공원 가중합 0~100",
    )
    score_transit = models.FloatField(
        help_text="지하철 1km anchor + 버스 면적당 밀도 p95 가중합 0~100",
    )

    class Meta:
        db_table = "current_gu"
        verbose_name = "자치구 최신 score"
        verbose_name_plural = "자치구 최신 score"
        constraints = [
            models.CheckConstraint(
                check=Q(score_amenity__gte=0, score_amenity__lte=100),
                name="ck_current_gu_amenity",
            ),
            models.CheckConstraint(
                check=Q(score_transit__gte=0, score_transit__lte=100),
                name="ck_current_gu_transit",
            ),
            models.CheckConstraint(
                check=Q(score_rent__gte=0, score_rent__lte=100) | Q(score_rent__isnull=True),
                name="ck_current_gu_rent",
            ),
        ]


class CurrentLdong(models.Model):
    """법정동 467개 최신 score 캐시. RDS `current_ldong` 테이블."""

    ldong = models.OneToOneField(
        "regions.Ldong",
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="ldong_code",
        related_name="current_score",
        help_text="법정동 코드 (RDS current_ldong.ldong_code)",
    )
    score_rent = models.FloatField(
        null=True,
        blank=True,
        help_text="최근 1년 환산월세/㎡ 기반 score. 거래 0 동은 NULL",
    )
    score_amenity = models.FloatField(
        help_text="생활/의료/공원 가중합 0~100",
    )
    score_transit = models.FloatField(
        help_text="지하철 1km anchor + 버스 면적당 밀도 p95 가중합 0~100",
    )

    class Meta:
        db_table = "current_ldong"
        verbose_name = "법정동 최신 score"
        verbose_name_plural = "법정동 최신 score"
        constraints = [
            models.CheckConstraint(
                check=Q(score_amenity__gte=0, score_amenity__lte=100),
                name="ck_current_ldong_amenity",
            ),
            models.CheckConstraint(
                check=Q(score_transit__gte=0, score_transit__lte=100),
                name="ck_current_ldong_transit",
            ),
            models.CheckConstraint(
                check=Q(score_rent__gte=0, score_rent__lte=100) | Q(score_rent__isnull=True),
                name="ck_current_ldong_rent",
            ),
        ]


class CurrentAdong(models.Model):
    """행정동 최신 score 캐시. RDS `current_adong` 테이블."""

    adong = models.OneToOneField(
        "regions.Adong",
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="adong_code",
        related_name="current_score",
        help_text="행정동 코드 (RDS current_adong.adong_code)",
    )
    score_rent = models.FloatField(
        null=True,
        blank=True,
        help_text="최근 1년 환산월세/㎡ 기반 score. 거래 0 동은 NULL",
    )
    score_amenity = models.FloatField(
        help_text="생활/의료/공원 가중합 0~100",
    )
    score_transit = models.FloatField(
        help_text="지하철 1km anchor + 버스 면적당 밀도 p95 가중합 0~100",
    )

    class Meta:
        db_table = "current_adong"
        verbose_name = "행정동 최신 score"
        verbose_name_plural = "행정동 최신 score"
        constraints = [
            models.CheckConstraint(
                check=Q(score_amenity__gte=0, score_amenity__lte=100),
                name="ck_current_adong_amenity",
            ),
            models.CheckConstraint(
                check=Q(score_transit__gte=0, score_transit__lte=100),
                name="ck_current_adong_transit",
            ),
            models.CheckConstraint(
                check=Q(score_rent__gte=0, score_rent__lte=100) | Q(score_rent__isnull=True),
                name="ck_current_adong_rent",
            ),
        ]
