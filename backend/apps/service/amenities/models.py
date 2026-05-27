"""
Amenity 모델 — sub-plan 2J 재구성 (schema.dbml line 365~400 정합).

Phase 2 구조:
- Amenity: store/park/library/univ/subway_station/bus_stop 6개 원천을 17종
  category로 통합한 단일 derived 테이블. score / 동상세 / 비교 / 지도 카운트
  단일 입력으로 사용.
- AmenityAdong / AmenityLdong: amenity ↔ adong/ldong N:M 매핑 분리
  (기존 dong FK 1:1 → N:M).

CHECK 화이트리스트:
- ck_amenity_category 17종 (CATEGORY_CHOICES)
- ck_amenity_source_table 6종 (SOURCE_TABLE_CHOICES)

uq_amenity_source: (source_table, source_id) unique.
"""

from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.db import models


# ---------------------------------------------------------------------------
# CHECK 화이트리스트 — schema.dbml ck_amenity_category / ck_amenity_source_table
# ---------------------------------------------------------------------------
CATEGORY_CHOICES = [
    ("convenience", "편의점"),
    ("mart", "마트"),
    ("restaurant", "음식점"),
    ("cafe", "카페"),
    ("studycafe", "스터디카페"),
    ("hospital", "병원"),
    ("dental", "치과"),
    ("pharmacy", "약국"),
    ("laundry", "세탁소"),
    ("oliveyoung", "올리브영"),
    ("gym", "체육시설"),
    ("etc", "기타"),
    ("park", "공원"),
    ("library", "도서관"),
    ("university", "대학교"),
    ("subway_station", "지하철역"),
    ("bus_stop", "버스정류장"),
]

SOURCE_TABLE_CHOICES = [
    ("store", "store"),
    ("park", "park"),
    ("library", "library"),
    ("univ", "univ"),
    ("subway_station", "subway_station"),
    ("bus_stop", "bus_stop"),
]


# ---------------------------------------------------------------------------
# Amenity (화면용 derived) — schema.dbml line 365~376
# ---------------------------------------------------------------------------


class Amenity(models.Model):
    """편의시설 한 건 (화면용 derived).

    schema.dbml `amenity` 테이블 1:1 매핑. PK는 BigAutoField (bigserial).
    """

    id = models.BigAutoField(primary_key=True)
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        help_text="시설 카테고리 (17종, ck_amenity_category)",
    )
    name = models.CharField(
        max_length=200,
        help_text=(
            "시설 명칭. park는 원천 name+\" \"+park.category 결합 "
            "(예: \"장미공원 어린이공원\"). 그 외는 원천 name 그대로."
        ),
    )
    location = gis_models.PointField(
        srid=4326,
        help_text="시설 위치 (WGS84). GiST 인덱스.",
    )
    source_table = models.CharField(
        max_length=30,
        choices=SOURCE_TABLE_CHOICES,
        help_text="원천 테이블명 (6종, ck_amenity_source_table)",
    )
    source_id = models.CharField(
        max_length=64,
        help_text=(
            "원천 PK 값 그대로. store.id / park.id / library.id / univ.id / "
            "subway_station.id / bus_stop.id"
        ),
    )

    # sub-plan 4.5C: created_at/updated_at 제거 (schema.dbml 정본에 없음, RDS 이전 호환).

    class Meta:
        db_table = "amenity"
        verbose_name = "생활시설"
        verbose_name_plural = "생활시설"
        indexes = [
            models.Index(fields=["category"]),
            GistIndex(fields=["location"], name="amenity_location_gist_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_table", "source_id"], name="uq_amenity_source"
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.category}] {self.name}"


# ---------------------------------------------------------------------------
# AmenityAdong / AmenityLdong — amenity ↔ 행정/법정동 N:M (schema.dbml 378~400)
# ---------------------------------------------------------------------------


class AmenityAdong(models.Model):
    """amenity ↔ adong N:M. schema.dbml `amenity_adong` 테이블."""

    amenity = models.ForeignKey(
        Amenity,
        on_delete=models.CASCADE,
        db_column="amenity_id",
        related_name="adong_links",
    )
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.CASCADE,
        db_column="adong_code",
        related_name="amenity_links",
    )

    class Meta:
        db_table = "amenity_adong"
        verbose_name = "생활시설 ↔ 행정동"
        verbose_name_plural = "생활시설 ↔ 행정동"
        unique_together = [("amenity", "adong")]
        indexes = [
            models.Index(fields=["amenity"]),
            models.Index(fields=["adong"]),
        ]

    def __str__(self) -> str:
        return f"{self.amenity_id} ↔ {self.adong_id}"


class AmenityLdong(models.Model):
    """amenity ↔ ldong N:M. schema.dbml `amenity_ldong` 테이블."""

    amenity = models.ForeignKey(
        Amenity,
        on_delete=models.CASCADE,
        db_column="amenity_id",
        related_name="ldong_links",
    )
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.CASCADE,
        db_column="ldong_code",
        related_name="amenity_links",
    )

    class Meta:
        db_table = "amenity_ldong"
        verbose_name = "생활시설 ↔ 법정동"
        verbose_name_plural = "생활시설 ↔ 법정동"
        unique_together = [("amenity", "ldong")]
        indexes = [
            models.Index(fields=["amenity"]),
            models.Index(fields=["ldong"]),
        ]

    def __str__(self) -> str:
        return f"{self.amenity_id} ↔ {self.ldong_id}"
