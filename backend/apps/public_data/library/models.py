"""sub-plan 2N — Library / LibraryHours 모델 신설.

schema.dbml line 333~358 정합. 변경 요약:
- Library 신설: id varchar(20) (Seoul Open API LBRRY_SEQ_NO 그대로),
  name, library_type (CHECK 2종), remark(자유 텍스트, NULL 허용),
  location(point, 4326), ldong/adong FK.
- LibraryHours 신설: composite PK = (library_id, day_type),
  day_type CHECK 7종 (MON~SUN), time_open/time_close, is_irregular.

데이터 출처: Seoul Open API 두 endpoint(공공도서관/작은도서관). 좌표 lock —
XCNTS=lat / YDNTS=lon. ldong_code/adong_code = ST_Within(location, *.boundary).
"""

from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.db import models
from django.db.models import Q


# ---------------------------------------------------------------------------
# LIBRARY_TYPE 2종 (schema.dbml CHECK ck_library_library_type)
# ---------------------------------------------------------------------------

LIBRARY_TYPE_CHOICES = [
    ("공공도서관", "공공도서관"),
    ("작은도서관", "작은도서관"),
]


# ---------------------------------------------------------------------------
# DAY_TYPE 7종 (schema.dbml CHECK ck_library_hours_day_type)
# ---------------------------------------------------------------------------

DAY_TYPE_CHOICES = [
    ("MON", "월"),
    ("TUE", "화"),
    ("WED", "수"),
    ("THU", "목"),
    ("FRI", "금"),
    ("SAT", "토"),
    ("SUN", "일"),
]


# ---------------------------------------------------------------------------
# 마스터
# ---------------------------------------------------------------------------


class Library(models.Model):
    """도서관 마스터.

    id: varchar(20). Seoul Open API LBRRY_SEQ_NO 그대로.
    공공/작은 두 endpoint 사이 중복 0 검증됨.
    library_type: CHECK ck_library_library_type 2종.
    location: ST_SetSRID(ST_MakePoint(YDNTS, XCNTS), 4326) — XCNTS=lat / YDNTS=lon.
    """

    id = models.CharField(
        max_length=20,
        primary_key=True,
        help_text=(
            "Seoul Open API LBRRY_SEQ_NO 그대로. "
            "공공/작은 두 endpoint 사이 중복 0 검증됨"
        ),
    )
    name = models.CharField(
        max_length=100,
        help_text=(
            "LBRRY_NAME 그대로. "
            "폐관 [폐관]/[페관] 접두사 42건은 적재 대상 외"
        ),
    )
    library_type = models.CharField(
        max_length=20,
        choices=LIBRARY_TYPE_CHOICES,
        help_text=(
            "공공도서관/작은도서관 "
            "(LBRRY_SE_NAME, CHECK ck_library_library_type 2종)"
        ),
    )
    remark = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "비정형 운영 정보 통합. 시즌 변동/점심 분리/N째주/N·M주/부분실/"
            "리모델링/휴관중/특정 휴일 등의 자유 텍스트. 표준 운영 시 NULL"
        ),
    )
    location = gis_models.PointField(
        srid=4326,
        help_text=(
            "ST_SetSRID(ST_MakePoint(YDNTS, XCNTS), 4326) — "
            "XCNTS=lat / YDNTS=lon (실측 lock)"
        ),
    )
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="ldong_code",
        related_name="libraries",
        help_text="ST_Within(location, ldong.boundary). 다중 매칭 시 면적 최소",
    )
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="adong_code",
        related_name="libraries",
        help_text="ST_Within(location, adong.boundary). 다중 매칭 시 면적 최소",
    )

    class Meta:
        db_table = "library"
        verbose_name = "도서관"
        verbose_name_plural = "도서관"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                check=Q(
                    library_type__in=[choice[0] for choice in LIBRARY_TYPE_CHOICES]
                ),
                name="ck_library_library_type",
            ),
        ]
        indexes = [
            GistIndex(fields=["location"], name="library_location_gist_idx"),
            models.Index(fields=["library_type"], name="ix_library_library_type"),
            models.Index(fields=["ldong"], name="ix_library_ldong"),
            models.Index(fields=["adong"], name="ix_library_adong"),
        ]

    def __str__(self) -> str:
        return f"{self.id} {self.name}"


# ---------------------------------------------------------------------------
# 운영 시간 (요일 단위)
# ---------------------------------------------------------------------------


class LibraryHours(models.Model):
    """도서관 운영 시간 (요일 단위). composite PK = (library_id, day_type).

    day_type: CHECK ck_library_hours_day_type 7종 (MON/TUE/WED/THU/FRI/SAT/SUN).
    is_irregular: 시즌 변동/점심 분리/N째주 등 비정형 운영 시 true.
    """

    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        db_column="library_id",
        related_name="hours",
    )
    day_type = models.CharField(
        max_length=10,
        choices=DAY_TYPE_CHOICES,
        help_text=(
            "MON/TUE/WED/THU/FRI/SAT/SUN "
            "(CHECK ck_library_hours_day_type 7종)"
        ),
    )
    time_open = models.TimeField(help_text="개관 시각")
    time_close = models.TimeField(help_text="폐관 시각")
    is_irregular = models.BooleanField(
        default=False,
        help_text=(
            "요일 단위 불규칙 표시. "
            "시즌 변동/점심 분리/N째주 등 비정형 적용 시 true"
        ),
    )

    class Meta:
        db_table = "library_hours"
        verbose_name = "도서관 운영 시간"
        verbose_name_plural = "도서관 운영 시간"
        unique_together = [("library", "day_type")]
        constraints = [
            models.CheckConstraint(
                check=Q(
                    day_type__in=[choice[0] for choice in DAY_TYPE_CHOICES]
                ),
                name="ck_library_hours_day_type",
            ),
        ]
        indexes = [
            models.Index(fields=["library"], name="ix_library_hours_library"),
            models.Index(fields=["day_type"], name="ix_library_hours_day_type"),
        ]

    def __str__(self) -> str:
        return f"{self.library_id} {self.day_type}"
