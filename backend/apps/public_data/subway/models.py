"""
Subway 모델 — schema.dbml line 216~242 정합 (sub-plan 4.5B).

- SubwayStation : 서울시 지하철역 마스터. PK varchar(20) (schema.dbml).
- SubwayCongestion : 지하철 혼잡도.
- NearestSubwayAdong / NearestSubwayLdong : schema.dbml line 449~473 (sub-plan 2L 신설).

sub-plan 4.5B 정합:
- SubwayStation PK: BigAutoField → CharField(max_length=20). 'id varchar(20)'.
- SubwayStation: legacy `adong FK`(neighborhoods.Adong) 제거 → adong/ldong FK 정합.
  schema.dbml ldong_code/adong_code NOT NULL.
- SubwayCongestion: PK (station_id, day_type, direction, express_yn, time).
  station FK는 새 varchar PK에 맞춰 db_column 'station_id' 유지.

sub-plan 7G-C (결정 4A):
- legacy NearestSubway(neighborhoods.Adong FK) 모델 및 nearest_subway 테이블 완전 폐기.
  NearestSubwayAdong / NearestSubwayLdong이 대체. compute_nearest_subway.py 폐기.
"""

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.db.models import Q


# ---------------------------------------------------------------------------
# 마스터
# ---------------------------------------------------------------------------


class SubwayStation(models.Model):
    """지하철역 (RDS subway_station 마스터). schema.dbml line 216~226."""

    # PK: schema.dbml 'id varchar(20)'.
    id = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="역 ID (RDS subway_station.id, varchar(20)).",
    )
    name = models.CharField(max_length=100, help_text="역명 (예: '충무로')")
    line = models.CharField(max_length=20, help_text="노선 (예: '3호선')")
    # 행정동 FK. regions snapshot 교체 시 임시 NULL 허용 후 updater가 다시 채운다.
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subway_stations",
        db_column="adong_code",
        help_text="행정동. regions snapshot 교체 시 NULL 허용.",
    )
    # 법정동 FK. regions snapshot 교체 시 임시 NULL 허용 후 updater가 다시 채운다.
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subway_stations",
        db_column="ldong_code",
        help_text="법정동. regions snapshot 교체 시 NULL 허용.",
    )
    location = gis_models.PointField(srid=4326, help_text="역 위치 (WGS84). GiST 인덱스.")

    class Meta:
        db_table = "subway_station"
        verbose_name = "지하철역"
        verbose_name_plural = "지하철역"
        indexes = [
            models.Index(fields=["name"]),
        ]
        ordering = ["line", "name"]

    def __str__(self) -> str:
        return f"{self.name}({self.line})"


# ---------------------------------------------------------------------------
# NearestSubway v2 — Adong / Ldong (schema.dbml line 449~473)
#
# sub-plan 7G-C (결정 4A): legacy NearestSubway(neighborhoods.Adong FK) 폐기.
# 이하 Adong/Ldong 기반 캐시만 사용.
# ---------------------------------------------------------------------------


class NearestSubwayAdong(models.Model):
    """행정동별 가까운 지하철역 top-3 사전 계산 캐시 (Adong FK 기반)."""

    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.CASCADE,
        db_column="adong_code",
        related_name="nearest_subways",
    )
    station_name = models.CharField(max_length=100, help_text="지하철역 이름 (비정규화)")
    distance_m = models.FloatField(help_text="측지선 m (>= 0)")

    class Meta:
        db_table = "nearest_subway_adong"
        verbose_name = "가까운 지하철역 (행정동, 사전계산)"
        verbose_name_plural = "가까운 지하철역 (행정동, 사전계산)"
        unique_together = [("adong", "station_name")]
        constraints = [
            models.CheckConstraint(
                check=Q(distance_m__gte=0),
                name="ck_nearest_subway_adong_distance",
            ),
        ]
        indexes = [
            models.Index(fields=["station_name"], name="ix_nearest_subway_adong_name"),
        ]
        ordering = ["adong", "distance_m", "station_name"]

    def __str__(self) -> str:
        return f"{self.adong_id} {self.station_name} ({self.distance_m:.0f}m)"


class NearestSubwayLdong(models.Model):
    """법정동별 가까운 지하철역 top-3 사전 계산 캐시 (Ldong FK 기반)."""

    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.CASCADE,
        db_column="ldong_code",
        related_name="nearest_subways",
    )
    station_name = models.CharField(max_length=100, help_text="지하철역 이름 (비정규화)")
    distance_m = models.FloatField(help_text="측지선 m (>= 0)")

    class Meta:
        db_table = "nearest_subway_ldong"
        verbose_name = "가까운 지하철역 (법정동, 사전계산)"
        verbose_name_plural = "가까운 지하철역 (법정동, 사전계산)"
        unique_together = [("ldong", "station_name")]
        constraints = [
            models.CheckConstraint(
                check=Q(distance_m__gte=0),
                name="ck_nearest_subway_ldong_distance",
            ),
        ]
        indexes = [
            models.Index(fields=["station_name"], name="ix_nearest_subway_ldong_name"),
        ]
        ordering = ["ldong", "distance_m", "station_name"]

    def __str__(self) -> str:
        return f"{self.ldong_id} {self.station_name} ({self.distance_m:.0f}m)"


# ---------------------------------------------------------------------------
# 혼잡도 — schema.dbml line 228~239
# ---------------------------------------------------------------------------


class SubwayCongestion(models.Model):
    """지하철 혼잡도.

    schema.dbml PK = (station_id, day_type, direction, express_yn, time).
    day_type/direction/express_yn 한글값 보존.
    """

    station = models.ForeignKey(
        SubwayStation,
        on_delete=models.CASCADE,
        related_name="congestions",
        db_column="station_id",
    )
    day_type = models.CharField(
        max_length=20,
        help_text="평일/토요일/일요일/휴일 (CHECK ck_subway_congestion_day_type 4종)",
    )
    direction = models.CharField(
        max_length=20,
        help_text="상선/하선/내선/외선 (CHECK ck_subway_congestion_direction 4종)",
    )
    express_yn = models.CharField(
        max_length=10,
        help_text="일반/급행 (CHECK ck_subway_congestion_express_yn 2종)",
    )
    time = models.TimeField(help_text="시간대")
    congestion = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="혼잡도 % (서울교통공사 기준 100=정원, 0~200+ 가능)",
    )

    class Meta:
        db_table = "subway_congestion"
        verbose_name = "지하철 혼잡도"
        verbose_name_plural = "지하철 혼잡도"
        unique_together = [
            ("station", "day_type", "direction", "express_yn", "time"),
        ]
        indexes = [
            models.Index(fields=["station", "day_type"]),
            models.Index(fields=["day_type", "time"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.station_id} {self.day_type}/{self.direction}/{self.express_yn} "
            f"{self.time} = {self.congestion}"
        )
