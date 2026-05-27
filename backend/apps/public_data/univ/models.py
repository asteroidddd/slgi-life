"""sub-plan 2M — Univ / UnivAdong / UnivLdong 모델 신설.

schema.dbml line 301~331 정합. 변경 요약:
- Univ 신설: id varchar(5) (type 1글자 U/C/I/E/B/P/V/M + 001~999, type별 가나다 정렬),
  name, school_type (CHECK 8종), boundary(multipolygon, 4326), location(point, 4326).
- UnivAdong / UnivLdong 신설: 다대다 매핑. composite PK = (univ_id, *_code).

데이터 출처: OSM 보강 데이터(이름) + 사용자 보강. location = ST_PointOnSurface(boundary).
"""

from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.db import models
from django.db.models import Q


# ---------------------------------------------------------------------------
# SCHOOL_TYPE 8종 (schema.dbml CHECK ck_univ_school_type)
# ---------------------------------------------------------------------------

SCHOOL_TYPE_CHOICES = [
    ("일반대학", "일반대학"),
    ("전문대학", "전문대학"),
    ("산업대학", "산업대학"),
    ("교육대학", "교육대학"),
    ("방송통신대학", "방송통신대학"),
    ("기능대학", "기능대학"),
    ("전공대학", "전공대학"),
    ("각종대학(대학)", "각종대학(대학)"),
]


# ---------------------------------------------------------------------------
# 마스터
# ---------------------------------------------------------------------------


class Univ(models.Model):
    """대학 마스터.

    id: varchar(5). type 1글자(U/C/I/E/B/P/V/M) + 001~999. type별 가나다 정렬.
    school_type: CHECK ck_univ_school_type 8종.
    location: ST_PointOnSurface(boundary).
    """

    id = models.CharField(
        max_length=5,
        primary_key=True,
        help_text="type 1글자(U/C/I/E/B/P/V/M) + 001~999. type별 가나다 정렬",
    )
    name = models.CharField(
        max_length=200,
        help_text="OSM name 또는 사용자 보강",
    )
    school_type = models.CharField(
        max_length=20,
        choices=SCHOOL_TYPE_CHOICES,
        help_text=(
            "일반대학/전문대학/산업대학/교육대학/방송통신대학/"
            "기능대학/전공대학/각종대학(대학) (CHECK ck_univ_school_type 8종)"
        ),
    )
    boundary = gis_models.MultiPolygonField(
        srid=4326,
        help_text="대학 경계 (WGS84)",
    )
    location = gis_models.PointField(
        srid=4326,
        help_text="ST_PointOnSurface(boundary) (WGS84)",
    )

    class Meta:
        db_table = "univ"
        verbose_name = "대학"
        verbose_name_plural = "대학"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                check=Q(
                    school_type__in=[choice[0] for choice in SCHOOL_TYPE_CHOICES]
                ),
                name="ck_univ_school_type",
            ),
        ]
        indexes = [
            GistIndex(fields=["boundary"], name="univ_boundary_gist_idx"),
            GistIndex(fields=["location"], name="univ_location_gist_idx"),
            models.Index(fields=["school_type"], name="ix_univ_school_type"),
        ]

    def __str__(self) -> str:
        return f"{self.id} {self.name}"


# ---------------------------------------------------------------------------
# 다대다 매핑
# ---------------------------------------------------------------------------


class UnivAdong(models.Model):
    """대학-행정동 다대다 매핑. composite PK = (univ_id, adong_code)."""

    univ = models.ForeignKey(
        Univ,
        on_delete=models.CASCADE,
        db_column="univ_id",
        related_name="adong_links",
    )
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.CASCADE,
        db_column="adong_code",
        related_name="univ_links",
    )

    class Meta:
        db_table = "univ_adong"
        verbose_name = "대학 ↔ 행정동"
        verbose_name_plural = "대학 ↔ 행정동"
        unique_together = [("univ", "adong")]
        indexes = [
            models.Index(fields=["univ"], name="ix_univ_adong_univ"),
            models.Index(fields=["adong"], name="ix_univ_adong_adong"),
        ]

    def __str__(self) -> str:
        return f"{self.univ_id} ↔ {self.adong_id}"


class UnivLdong(models.Model):
    """대학-법정동 다대다 매핑. composite PK = (univ_id, ldong_code)."""

    univ = models.ForeignKey(
        Univ,
        on_delete=models.CASCADE,
        db_column="univ_id",
        related_name="ldong_links",
    )
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.CASCADE,
        db_column="ldong_code",
        related_name="univ_links",
    )

    class Meta:
        db_table = "univ_ldong"
        verbose_name = "대학 ↔ 법정동"
        verbose_name_plural = "대학 ↔ 법정동"
        unique_together = [("univ", "ldong")]
        indexes = [
            models.Index(fields=["univ"], name="ix_univ_ldong_univ"),
            models.Index(fields=["ldong"], name="ix_univ_ldong_ldong"),
        ]

    def __str__(self) -> str:
        return f"{self.univ_id} ↔ {self.ldong_id}"
