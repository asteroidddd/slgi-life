"""
Bus 모델 — schema.dbml line 243~264 정합 (sub-plan 4.5B).

- BusStop       : 서울시 버스 정류장. PK varchar(20).
- BusCongestion : 버스 혼잡도. PK = (bus_stop_id, date, time).

sub-plan 4.5B 정합:
- BusStop PK: BigAutoField → CharField(max_length=20). 'id varchar(20)'.
- BusStop: legacy `dong FK`(neighborhoods.Dong) 제거 → adong/ldong FK (nullable).
  schema.dbml line 247~248 ldong_code/adong_code NOT NULL 없음(nullable 허용).
- BusCongestion: congestion NOT NULL (schema.dbml line 259).

응답 dict key 보존(lock 1) — frontend가 BusStop을 직접 응답 받는 위치는 없음
(neighborhoods/transit-congestion view는 stop_count 정수만 반환).
"""

from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import BrinIndex, GistIndex
from django.db import models


# ---------------------------------------------------------------------------
# 마스터
# ---------------------------------------------------------------------------


class BusStop(models.Model):
    """버스 정류장. schema.dbml line 243~250."""

    # PK: schema.dbml 'id varchar(20)'.
    id = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="정류장 ID (RDS bus_stop.id, varchar(20)).",
    )
    stop_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text=(
            "정류소번호 (서울 BIS arsId). RDS bus_stop.stop_number 1:1. "
            "schema.dbml NULL 허용 (line 245)."
        ),
    )
    name = models.CharField(max_length=100, help_text="정류장 명칭 (NOT NULL)")

    # 행정동/법정동 FK (nullable — schema.dbml NOT NULL 미표기).
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bus_stops",
        db_column="adong_code",
        help_text="행정동 (nullable).",
    )
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bus_stops",
        db_column="ldong_code",
        help_text="법정동 (nullable).",
    )

    location = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text=(
            "정류장 위치 (WGS84). 매칭 불가 시 NULL 보존 "
            "(가상·차고지·미정차 등, schema.dbml line 249)."
        ),
    )

    class Meta:
        db_table = "bus_stop"
        verbose_name = "버스 정류장"
        verbose_name_plural = "버스 정류장"
        indexes = [
            models.Index(fields=["adong"]),
            models.Index(fields=["ldong"]),
            models.Index(fields=["stop_number"]),
            GistIndex(fields=["location"], name="busstop_location_gist_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.stop_number})" if self.stop_number else self.name


# ---------------------------------------------------------------------------
# 혼잡도 — schema.dbml line 255~264
# ---------------------------------------------------------------------------


class BusCongestion(models.Model):
    """버스 혼잡도. schema.dbml PK = (bus_stop_id, date, time)."""

    bus_stop = models.ForeignKey(
        BusStop,
        on_delete=models.CASCADE,
        related_name="congestions",
        db_column="bus_stop_id",
    )
    date = models.DateField(help_text="기준일")
    time = models.TimeField(help_text="시간대 0~23")
    congestion = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text=(
            "혼잡도 (RouteCongestionLevel API 응답값. 시간대·노선 평균. "
            "단위는 응답 그대로, 보통 0~210). NOT NULL."
        ),
    )

    class Meta:
        db_table = "bus_congestion"
        verbose_name = "버스 혼잡도"
        verbose_name_plural = "버스 혼잡도"
        unique_together = [("bus_stop", "date", "time")]
        indexes = [
            BrinIndex(fields=["date"], name="buscongestion_date_brin_idx"),
            models.Index(fields=["bus_stop", "-date"]),
        ]

    def __str__(self) -> str:
        return f"{self.bus_stop_id} {self.date} {self.time} = {self.congestion}"
