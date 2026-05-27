"""
RentDeal — schema.dbml line 159~177 정합 (sub-plan 4.5B).

전월세 실거래 1행. RDS rent_deal과 1:1.

schema.dbml 정합 (sub-plan 4.5B):
- PK: BigAutoField → CharField(max_length=60). 'id varchar(60)' (예: '11010100A260514001').
- 컬럼 정합:
  - housing_type: NOT NULL varchar(20) (5종 한글 raw).
  - ldong_code: nullable FK → regions.Ldong (db_column='ldong_code').
  - adong FK 제거 (schema.dbml에 없음).
  - contract_date (date, NOT NULL) ← 기존 deal_date 이름 변경.
  - construction_year (smallint) ← 기존 build_year 이름 변경.
  - area_m2 decimal(NULL 허용).
  - deposit bigint(NOT NULL).
  - monthly_rent integer(NOT NULL).
  - external_id / external_hash / created_at 제거 (schema.dbml에 없음).
  - housing_type 영문 enum(deal_type)도 제거 — 한글 housing_type 단일.

serializer / view는 응답 dict key를 보존한다 (lock 1, frontend 응답 0 변경):
- 응답 'deal_type' 키 ← housing_type 영문 매핑(serializer source).
- 응답 'date' 키 ← contract_date 매핑.
- 응답 'dong_name' / 'gu' ← ldong.name / ldong.gu.name 매핑.

frontend는 backend API만 호출. 본 model 변경 후에도 frontend 응답 dict key 0 변경 (lock 1).
"""

from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.db import models


# housing_type 한글 5종 (CHECK ck_rent_deal_housing_type, schema.dbml line 161).
HOUSING_TYPE_CHOICES = [
    ("아파트", "아파트"),
    ("연립다세대", "연립다세대"),
    ("다가구", "다가구"),
    ("단독", "단독"),
    ("오피스텔", "오피스텔"),
]

# 한글 housing_type ↔ 영문 deal_type 매핑 (serializer 응답 key 'deal_type' 보존용).
# legacy 응답 (sub-plan 2H 이전)에서 'deal_type'은 영문 enum 5종을 반환했음.
HOUSING_TYPE_TO_DEAL_TYPE: dict[str, str] = {
    "아파트": "apt",
    "오피스텔": "officetel",
    "연립다세대": "villa",
    "다가구": "dagagu",
    "단독": "danok",
}

# 역방향 (영문 → 한글) — explore/match 등 deal_types 필터 정규화에 사용.
DEAL_TYPE_TO_HOUSING_TYPE: dict[str, str] = {
    v: k for k, v in HOUSING_TYPE_TO_DEAL_TYPE.items()
}


class RentDeal(models.Model):
    """전/월세 실거래 한 건. RDS rent_deal과 1:1."""

    # PK: schema.dbml 'id varchar(60)'.
    id = models.CharField(
        max_length=60,
        primary_key=True,
        help_text=(
            "8자리 ldong + 1~2자 housing 코드 + YYMMDD + NNN, dash 없음. "
            "예: 11010100A260514001"
        ),
    )

    # 5종 한글 raw. schema.dbml CHECK ck_rent_deal_housing_type.
    housing_type = models.CharField(
        max_length=20,
        choices=HOUSING_TYPE_CHOICES,
        help_text="아파트, 연립다세대, 다가구, 단독, 오피스텔 (5종)",
    )

    # 법정동 FK. regions snapshot 교체 시 임시 NULL 허용.
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rent_deals",
        db_column="ldong_code",
        help_text="법정동. regions snapshot 교체 시 NULL 허용.",
    )

    # 행정동 FK. 법정동과 행정동은 N:M일 수 있으므로 확실한 공간 매핑만 채운다.
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.SET_NULL,
        related_name="rent_deals",
        db_column="adong_code",
        null=True,
        blank=True,
        help_text="행정동. 확실한 ldong 포함/동일 또는 신뢰 가능한 위치 매핑만 저장.",
    )

    # 지번 / 건물명 / 면적 (NULL 허용 — 응답 결측 시 그대로).
    jibun = models.CharField(
        max_length=50, null=True, blank=True, help_text="'법정동 + 지번' 원문 (NULL 허용)"
    )
    house_name = models.CharField(
        max_length=100, null=True, blank=True, help_text="건물명 (NULL 허용)"
    )
    area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="전용면적 ㎡. NULL 허용 (응답 결측 시 그대로 유지).",
    )

    # 층 / 건축연도.
    floor = models.SmallIntegerField(null=True, blank=True, help_text="층 (지하 음수)")
    construction_year = models.SmallIntegerField(
        null=True,
        blank=True,
        help_text="건축 연도. 응답 그대로 보존 (이상치 포함).",
    )

    # 금액 — schema.dbml bigint(deposit) / integer(monthly_rent).
    deposit = models.BigIntegerField(help_text="보증금 (만원, NOT NULL)")
    monthly_rent = models.IntegerField(help_text="월세 (만원, NOT NULL). 0이면 전세.")

    # 계약 일자 / 갱신.
    contract_date = models.DateField(help_text="계약일 (NOT NULL)")
    contract_end_date = models.DateField(null=True, blank=True, help_text="계약 종료일")
    contract_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="신규, 갱신 (CHECK ck_rent_deal_contract_type, NULL 허용)",
    )
    renewal_request_right_used = models.BooleanField(
        null=True, blank=True, help_text="갱신요구권 사용 여부"
    )
    previous_deposit = models.BigIntegerField(
        null=True, blank=True, help_text="종전 계약 보증금 (만원)"
    )
    previous_monthly_rent = models.IntegerField(
        null=True, blank=True, help_text="종전 계약 월세 (만원)"
    )

    # 위치 — 지번 보유 행은 외부 지오코딩 API 결과만 저장한다.
    location = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text=(
            "지번 보유 행의 외부 지오코딩 API 결과. 단독/다가구 또는 신뢰 불가 좌표는 NULL."
        ),
    )

    class Meta:
        db_table = "rent_deal"
        verbose_name = "전월세 실거래"
        verbose_name_plural = "전월세 실거래"
        indexes = [
            models.Index(fields=["ldong", "contract_date"]),
            models.Index(fields=["adong", "contract_date"], name="rent_deal_adong_contract_idx"),
            models.Index(fields=["housing_type", "contract_date"]),
            models.Index(fields=["housing_type"]),
            GistIndex(fields=["location"], name="rentdeal_location_gist_idx"),
        ]
        ordering = ["-contract_date"]

    def __str__(self) -> str:
        return (
            f"{self.contract_date} [{self.housing_type}] "
            f"{self.ldong_id} {self.deposit}/{self.monthly_rent}"
        )


class RentDealLdongAdongMap(models.Model):
    """Ldong to adong map for rent_deal.adong_code backfill.

    adong is NULL when one legal dong touches multiple admin dongs and cannot be
    mapped safely without row-level location evidence.
    """

    ldong = models.OneToOneField(
        "regions.Ldong",
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="rent_deal_adong_map",
        db_column="ldong_code",
        help_text="Legal dong. One mapping decision per ldong.",
    )
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rent_deal_ldong_maps",
        db_column="adong_code",
        help_text="Admin dong when this ldong maps to exactly one adong; otherwise NULL.",
    )

    class Meta:
        db_table = "rent_deal_ldong_adong_map"
        verbose_name = "rent deal ldong-adong map"
        verbose_name_plural = "rent deal ldong-adong maps"
        indexes = [
            models.Index(fields=["adong"], name="rent_ld_ad_map_adong_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.ldong_id} -> {self.adong_id or 'NULL'}"
