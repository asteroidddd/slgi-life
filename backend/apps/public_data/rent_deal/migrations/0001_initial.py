"""Sub-plan 2D — RentDeal 모델 신설 (realestate에서 이동).

state + database CreateModel. fresh migrate 시 realestate/0003 (drop) 직후
실행되어 rent_deal 테이블을 재생성한다. 단계 5 docker fresh migrate 환경에서
SLGI DB는 데이터 0행이므로 drop→recreate 비용은 무해.

컬럼 / 인덱스 / FK 구성은 realestate/0001+0002 누적 상태와 동일하다.
"""

import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("neighborhoods", "0002_alter_dong_code"),
        ("regions", "0003_remove_populations"),
    ]

    operations = [
        migrations.CreateModel(
            name="RentDeal",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "external_id",
                    models.CharField(
                        blank=True,
                        help_text="RDS rent_deal.id (Phase 1 신규). 신규 적재는 이 값으로 멱등 보장.",
                        max_length=64,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "deal_type",
                    models.CharField(
                        choices=[
                            ("apt", "아파트"),
                            ("officetel", "오피스텔"),
                            ("villa", "연립다세대"),
                            ("dagagu", "다가구"),
                            ("danok", "단독"),
                        ],
                        help_text="거래 유형 (영문 enum 5종). RDS housing_type 한글 → 영문 derived.",
                        max_length=20,
                    ),
                ),
                (
                    "housing_type",
                    models.CharField(
                        blank=True,
                        help_text="RDS housing_type 한글 raw (예: '아파트', '다가구', '연립다세대'). Phase 1 신규.",
                        max_length=30,
                    ),
                ),
                ("deal_date", models.DateField(help_text="계약일 (API의 dealYear/Month/Day 조합)")),
                (
                    "contract_end_date",
                    models.DateField(
                        blank=True, help_text="계약 종료일 (Phase 1 신규)", null=True
                    ),
                ),
                (
                    "contract_type",
                    models.CharField(
                        blank=True, help_text="계약 구분 (신규/갱신 등). Phase 1 신규.", max_length=20
                    ),
                ),
                (
                    "renewal_request_right_used",
                    models.BooleanField(
                        blank=True, help_text="갱신요구권 사용 여부. Phase 1 신규.", null=True
                    ),
                ),
                ("area_m2", models.FloatField(help_text="전용면적 (m^2)")),
                ("deposit", models.PositiveIntegerField(help_text="보증금 (만원)")),
                ("monthly_rent", models.PositiveIntegerField(help_text="월세 (만원). 0이면 전세.")),
                (
                    "previous_deposit",
                    models.PositiveIntegerField(
                        blank=True, help_text="종전 계약 보증금 (만원). Phase 1 신규.", null=True
                    ),
                ),
                (
                    "previous_monthly_rent",
                    models.PositiveIntegerField(
                        blank=True, help_text="종전 계약 월세 (만원). Phase 1 신규.", null=True
                    ),
                ),
                (
                    "floor",
                    models.SmallIntegerField(blank=True, help_text="층 (지하 음수)", null=True),
                ),
                (
                    "build_year",
                    models.PositiveSmallIntegerField(blank=True, help_text="건축 연도", null=True),
                ),
                (
                    "house_name",
                    models.CharField(
                        blank=True, help_text="건물명 (RDS house_name). Phase 1 신규.", max_length=200
                    ),
                ),
                (
                    "jibun",
                    models.CharField(
                        blank=True,
                        help_text="'법정동 + 지번' 원문 (예: '필동2가 84-1')",
                        max_length=64,
                    ),
                ),
                (
                    "geom",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True,
                        help_text="지번 중심점. RDS location 그대로 (SPEC 14.2 정책 충족).",
                        null=True,
                        srid=4326,
                    ),
                ),
                (
                    "external_hash",
                    models.CharField(
                        blank=True,
                        help_text="기존 적재용 deal key 해시 (Phase 1 이전 데이터 호환). 신규 적재는 external_id 사용.",
                        max_length=64,
                        null=True,
                        unique=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "dong",
                    models.ForeignKey(
                        help_text="법정동→행정동 매핑 후 결정된 행정동. RDS adong_code 또는 location ST_Contains 백필.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rent_deals",
                        to="neighborhoods.dong",
                    ),
                ),
                (
                    "ldong",
                    models.ForeignKey(
                        blank=True,
                        help_text="법정동 (Phase 1 신규). RDS ldong_code 직접 매핑.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rent_deals",
                        to="regions.ldong",
                    ),
                ),
            ],
            options={
                "verbose_name": "전월세 실거래",
                "verbose_name_plural": "전월세 실거래",
                "db_table": "rent_deal",
                "ordering": ["-deal_date"],
                "indexes": [
                    models.Index(fields=["dong", "deal_date"], name="rent_deal_dong_id_e5b674_idx"),
                    models.Index(
                        fields=["ldong", "deal_date"], name="rent_deal_ldong_i_c678f0_idx"
                    ),
                    models.Index(
                        fields=["deal_type", "deal_date"], name="rent_deal_deal_ty_dda379_idx"
                    ),
                    models.Index(fields=["housing_type"], name="rent_deal_housing_438bed_idx"),
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["geom"], name="rentdeal_geom_gist_idx"
                    ),
                ],
            },
        ),
    ]
