"""
공원 (Park) 모델 — schema.dbml line 268~299 정합 (sub-plan 4.5C).

DP_DB park 1,886행 + park_adong / park_ldong 다대다 관계 테이블을 1:1로 매핑.

sub-plan 4.5C 정합:
- PK: varchar(64) → varchar(50). 'id varchar(50)' (schema.dbml line 269).
- name: NOT NULL (이미 OK).
- category: blank=False, NOT NULL (schema.dbml line 271).
- area_m2: NOT NULL (schema.dbml line 272). max_digits/decimal_places 보존.
- boundary: NOT NULL (schema.dbml line 273).
- location: NOT NULL (schema.dbml line 274).
"""

from django.contrib.gis.db import models as gis_models
from django.db import models


class Park(models.Model):
    """공원. DP_DB `park` 1,886행. schema.dbml line 268~275."""

    id = models.CharField(
        max_length=50,
        primary_key=True,
        help_text=(
            "공원 ID (RDS park.id, varchar(50)). "
            "SHP UPIS_SHP_ZON216의 ID에서 끝 4자리 추출 후 P prefix. "
            "예: 생활서비스시설_공원_0033 → P0033"
        ),
    )
    name = models.CharField(max_length=200, help_text="공원 이름 (NOT NULL)")
    category = models.CharField(
        max_length=50,
        help_text=(
            "공원 분류 (NOT NULL). 근린공원/어린이공원/도시자연공원/마을마당/광장 "
            "등 SHP LABEL의 첫 분류 토큰"
        ),
    )
    area_m2 = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        help_text="면적 (m^2, NOT NULL)",
    )
    boundary = gis_models.MultiPolygonField(
        srid=4326,
        help_text="공원 경계 (WGS84, NOT NULL)",
    )
    location = gis_models.PointField(
        srid=4326,
        help_text="중심점 (WGS84, NOT NULL)",
    )

    class Meta:
        db_table = "park"
        verbose_name = "공원"
        verbose_name_plural = "공원"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["category"]),
        ]

    def __str__(self) -> str:
        return self.name


class ParkAdong(models.Model):
    """공원-행정동 다대다 매핑. RDS `park_adong` 2,353행.

    sub-plan 2O — Adong 마스터 FK로 치환 (이전: neighborhoods.Adong FK + to_field='code').
    db_column은 `adong_code` 유지 → DB 변경 0. 클래스명 ParkAdong은 유지 (db_table=park_adong).
    """

    park = models.ForeignKey(
        Park, on_delete=models.CASCADE, related_name="park_dongs", db_column="park_id"
    )
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.CASCADE,
        related_name="park_dongs",
        db_column="adong_code",
    )

    class Meta:
        db_table = "park_adong"
        verbose_name = "공원-행정동 매핑"
        verbose_name_plural = "공원-행정동 매핑"
        unique_together = [("park", "adong")]

    def __str__(self) -> str:
        return f"{self.park_id} ↔ {self.adong_id}"


class ParkLdong(models.Model):
    """공원-법정동 다대다 매핑. RDS `park_ldong` 2,316행."""

    park = models.ForeignKey(
        Park, on_delete=models.CASCADE, related_name="park_ldongs", db_column="park_id"
    )
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.CASCADE,
        related_name="park_ldongs",
        db_column="ldong_code",
    )

    class Meta:
        db_table = "park_ldong"
        verbose_name = "공원-법정동 매핑"
        verbose_name_plural = "공원-법정동 매핑"
        unique_together = [("park", "ldong")]

    def __str__(self) -> str:
        return f"{self.park_id} ↔ {self.ldong_id}"
