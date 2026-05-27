"""
행정 단위 마스터 + 인접 모델 (Phase 1 — RDS 통합용).

RDS(`dp_db`) 측 24 테이블 중 행정 단위/인접에 해당하는 6개를 1:1로 매핑한다.
- Seoul / Gu / Ldong         : 마스터 (boundary + location)
- GuAdjacency / LdongAdjacency / AdongAdjacency : 양방향 인접 row 그대로 보존

LdongPopulation / AdongPopulation은 sub-plan 2C에서 `apps.public_data.populations`
로 이동했다 (DB 변경 0, ORM 인식만 이동).

Dong 모델·테이블은 sub-plan 7G-C(결정 5A)에서 완전 폐기되었다. 모든 행정동
참조는 Adong + 합성 score 컬럼 (current_score)으로 대체된다. AdongAdjacency
는 sub-plan 2O에서 Adong 마스터를 FK로 잡도록 치환되었다 (db_column 유지 → DB 변경 0).

DB 정책 (계획서 1·2):
- 모든 boundary는 MultiPolygonField(srid=4326)
- 모든 location/centroid는 PointField(srid=4326)
- PK는 RDS 비즈니스 키를 그대로 사용 (code 컬럼)
- db_table은 RDS 테이블명과 동일하게 맞춰 ETL을 INSERT…SELECT로 단순화
- Adjacency는 양방향 row 둘 다 보존 (RDS 형상 그대로) — unique_together만 적용
"""

from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.db import models


# ---------------------------------------------------------------------------
# 1. Seoul / Gu / Ldong — 마스터 (boundary + location)
# ---------------------------------------------------------------------------


class Seoul(models.Model):
    """서울시 1행. RDS `seoul` 테이블."""

    code = models.CharField(max_length=20, primary_key=True, help_text="서울시 코드 (RDS seoul.code)")
    name = models.CharField(max_length=100, help_text="이름 (예: '서울특별시')")
    area_m2 = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True, help_text="면적 (m^2)"
    )
    boundary = gis_models.MultiPolygonField(
        srid=4326, null=True, blank=True, help_text="서울시 경계 (WGS84)"
    )
    location = gis_models.PointField(
        srid=4326, null=True, blank=True, help_text="중심점 (WGS84)"
    )

    class Meta:
        db_table = "seoul"
        verbose_name = "서울"
        verbose_name_plural = "서울"

    def __str__(self) -> str:
        return self.name


class Gu(models.Model):
    """자치구 25개. RDS `gu` 테이블."""

    gu_code = models.CharField(
        max_length=20, primary_key=True, help_text="자치구 코드 (RDS gu.gu_code)"
    )
    name = models.CharField(max_length=100, help_text="구 이름 (예: '중구')")
    slug = models.SlugField(
        max_length=80,
        unique=True,
        null=True,
        blank=True,
        help_text="URL용 고유 식별자. gu.name과 동일값 (예: 강남구)",
    )
    area_m2 = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True, help_text="면적 (m^2)"
    )
    boundary = gis_models.MultiPolygonField(
        srid=4326, null=True, blank=True, help_text="구 경계 (WGS84)"
    )
    location = gis_models.PointField(
        srid=4326, null=True, blank=True, help_text="중심점 (WGS84)"
    )

    class Meta:
        db_table = "gu"
        verbose_name = "자치구"
        verbose_name_plural = "자치구"
        ordering = ["gu_code"]
        indexes = [
            GistIndex(fields=["boundary"], name="gu_boundary_gist_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class Ldong(models.Model):
    """법정동 467개. RDS `ldong` 테이블."""

    ldong_code = models.CharField(
        max_length=20, primary_key=True, help_text="법정동 코드 (RDS ldong.ldong_code)"
    )
    name = models.CharField(max_length=100, help_text="법정동 이름")
    slug = models.SlugField(
        max_length=80,
        unique=True,
        null=True,
        blank=True,
        help_text="URL용 고유 식별자. 패턴: <gu_name>-<name> (예: 강남구-신사동)",
    )
    gu = models.ForeignKey(
        Gu,
        on_delete=models.PROTECT,
        related_name="ldongs",
        db_column="gu_code",
        help_text="속한 자치구 (RDS ldong.gu_code)",
    )
    area_m2 = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True, help_text="면적 (m^2)"
    )
    boundary = gis_models.MultiPolygonField(
        srid=4326, null=True, blank=True, help_text="법정동 경계 (WGS84)"
    )
    location = gis_models.PointField(
        srid=4326, null=True, blank=True, help_text="중심점 (WGS84)"
    )

    class Meta:
        db_table = "ldong"
        verbose_name = "법정동"
        verbose_name_plural = "법정동"
        ordering = ["ldong_code"]
        indexes = [
            models.Index(fields=["gu"]),
            GistIndex(fields=["boundary"], name="ldong_boundary_gist_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.gu.name} {self.name}"


class Adong(models.Model):
    """행정동. RDS `adong` 테이블 (schema.dbml line 119~127).

    sub-plan 2J 신설. legacy `apps.service.neighborhoods.Dong`(=행정동) 모델·테이블은
    sub-plan 7G-C(결정 5A)에서 완전 폐기되어 Adong이 단일 행정동 마스터다.
    Adong 모델은 sub-plan 2K/2L에서 score current_*/score_history adong-level
    참조용으로 신설되었으며, 7G-C 이후 행정동 표면 객체이기도 하다.

    schema.dbml에선 boundary/location/area_m2/slug 모두 NOT NULL이지만,
    기존 Gu/Ldong 모델 패턴(ETL 적재 전 NULL 허용)을 따라 null=True/blank=True
    유지. ETL/체크 제약 단계에서 NOT NULL 보장.
    """

    adong_code = models.CharField(
        max_length=20, primary_key=True, help_text="행정동 코드 (RDS adong.adong_code)"
    )
    gu = models.ForeignKey(
        Gu,
        on_delete=models.PROTECT,
        related_name="adongs",
        db_column="gu_code",
        help_text="속한 자치구 (RDS adong.gu_code)",
    )
    name = models.CharField(max_length=100, help_text="행정동 이름")
    slug = models.SlugField(
        max_length=80,
        unique=True,
        help_text="URL용 고유 식별자. 패턴: <gu_name>-<name> (예: 강남구-신사동)",
    )
    area_m2 = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True, help_text="면적 (m^2)"
    )
    boundary = gis_models.MultiPolygonField(
        srid=4326, null=True, blank=True, help_text="행정동 경계 (WGS84)"
    )
    location = gis_models.PointField(
        srid=4326, null=True, blank=True, help_text="중심점 (WGS84)"
    )

    class Meta:
        db_table = "adong"
        verbose_name = "행정동"
        verbose_name_plural = "행정동"
        ordering = ["adong_code"]
        indexes = [
            GistIndex(fields=["boundary"], name="adong_boundary_gist_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.gu.name} {self.name}"


# ---------------------------------------------------------------------------
# 2. Adjacency — Gu / Ldong / Adong (양방향 row 그대로 보존)
# ---------------------------------------------------------------------------


class GuAdjacency(models.Model):
    """자치구 인접. RDS `adjacent_gu` 108행 (양방향 보존).

    sub-plan 4.5A — schema.dbml 정합: db_column gu_code_a/_b → gu1_code/gu2_code.
    """

    gu_a = models.ForeignKey(
        Gu, on_delete=models.CASCADE, related_name="adjacency_a", db_column="gu1_code"
    )
    gu_b = models.ForeignKey(
        Gu, on_delete=models.CASCADE, related_name="adjacency_b", db_column="gu2_code"
    )

    class Meta:
        db_table = "adjacent_gu"
        verbose_name = "자치구 인접"
        verbose_name_plural = "자치구 인접"
        unique_together = [("gu_a", "gu_b")]
        indexes = [
            models.Index(fields=["gu_a"]),
            models.Index(fields=["gu_b"]),
        ]
        # a == b 방지는 ETL/체크 제약 단계에서 검증.

    def __str__(self) -> str:
        return f"{self.gu_a_id} ↔ {self.gu_b_id}"


class LdongAdjacency(models.Model):
    """법정동 인접. RDS `adjacent_ldong` 1,948행 (양방향 보존).

    sub-plan 4.5A — schema.dbml 정합: db_column ldong_code_a/_b → ldong1_code/ldong2_code.
    """

    ldong_a = models.ForeignKey(
        Ldong, on_delete=models.CASCADE, related_name="adjacency_a", db_column="ldong1_code"
    )
    ldong_b = models.ForeignKey(
        Ldong, on_delete=models.CASCADE, related_name="adjacency_b", db_column="ldong2_code"
    )

    class Meta:
        db_table = "adjacent_ldong"
        verbose_name = "법정동 인접"
        verbose_name_plural = "법정동 인접"
        unique_together = [("ldong_a", "ldong_b")]
        indexes = [
            models.Index(fields=["ldong_a"]),
            models.Index(fields=["ldong_b"]),
        ]

    def __str__(self) -> str:
        return f"{self.ldong_a_id} ↔ {self.ldong_b_id}"


class AdongAdjacency(models.Model):
    """행정동 인접. RDS `adjacent_adong` 2,444행.

    sub-plan 2O — Adong 마스터 FK로 치환 (이전: neighborhoods.Dong FK + to_field='code').
    db_column은 `adong_code_a`/`adong_code_b` 유지 → DB 변경 0.
    """

    adong_a = models.ForeignKey(
        "regions.Adong",
        on_delete=models.CASCADE,
        related_name="adjacency_a",
        db_column="adong1_code",
    )
    adong_b = models.ForeignKey(
        "regions.Adong",
        on_delete=models.CASCADE,
        related_name="adjacency_b",
        db_column="adong2_code",
    )

    class Meta:
        db_table = "adjacent_adong"
        verbose_name = "행정동 인접"
        verbose_name_plural = "행정동 인접"
        unique_together = [("adong_a", "adong_b")]
        indexes = [
            models.Index(fields=["adong_a"]),
            models.Index(fields=["adong_b"]),
        ]

    def __str__(self) -> str:
        return f"{self.adong_a_id} ↔ {self.adong_b_id}"


# ---------------------------------------------------------------------------
# 3. Population — sub-plan 2C에서 `apps.public_data.populations`로 이동.
#    (SeparateDatabaseAndState 패턴, DB 변경 0)
# ---------------------------------------------------------------------------
