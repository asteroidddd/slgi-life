"""sub-plan 4.5B — rent_deal 앱 RentDeal 모델을 schema.dbml line 159~177 정합.

변경 요약 (DB 0행 가정):
- PK: BigAutoField → CharField(max_length=60).
- 컬럼명: deal_date → contract_date, build_year → construction_year.
- area_m2 FloatField → DecimalField (NULL 허용).
- deposit/monthly_rent: PositiveIntegerField → BigIntegerField/IntegerField (schema.dbml bigint/integer 정합).
- previous_deposit/previous_monthly_rent: PositiveIntegerField → BigIntegerField/IntegerField.
- floor SmallInteger 유지. construction_year도 SmallInteger.
- house_name varchar(200) → varchar(100) (schema.dbml line 164).
- jibun varchar(64) → varchar(50) (schema.dbml line 163).
- housing_type varchar(30) → varchar(20) + choices 5종 한글 (CHECK ck_rent_deal_housing_type).
- dong FK (neighborhoods.Dong) 제거 (schema.dbml에 없음).
- ldong FK NOT NULL (schema.dbml line 162).
- deal_type 영문 enum 컬럼 제거 (한글 housing_type 단일).
- external_id / external_hash / created_at 제거.
- index 정리: dong/deal_type 인덱스 제거 → ldong/housing_type 인덱스 신설.
- GistIndex name 동일 (rentdeal_location_gist_idx).

DB 변경: state + database 모두 일관 적용 (DB 0행이라 drop/recreate 비용 무해).
"""

import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


HOUSING_TYPE_CHOICES_NEW = [
    ("아파트", "아파트"),
    ("연립다세대", "연립다세대"),
    ("다가구", "다가구"),
    ("단독", "단독"),
    ("오피스텔", "오피스텔"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("rent_deal", "0002_rename_geom_to_location"),
        ("regions", "0004_add_adong"),
    ]

    operations = [
        # ---- 인덱스 / FK 제거 단계 (DROP 순서) ----
        migrations.RemoveIndex(
            model_name="rentdeal",
            name="rent_deal_dong_id_e5b674_idx",
        ),
        migrations.RemoveIndex(
            model_name="rentdeal",
            name="rent_deal_ldong_i_c678f0_idx",
        ),
        migrations.RemoveIndex(
            model_name="rentdeal",
            name="rent_deal_deal_ty_dda379_idx",
        ),
        migrations.RemoveIndex(
            model_name="rentdeal",
            name="rent_deal_housing_438bed_idx",
        ),
        migrations.RemoveIndex(
            model_name="rentdeal",
            name="rentdeal_location_gist_idx",
        ),
        migrations.RemoveField(
            model_name="rentdeal",
            name="dong",
        ),
        # ---- 제거할 컬럼들 (schema.dbml에 없음) ----
        migrations.RemoveField(
            model_name="rentdeal",
            name="deal_type",
        ),
        migrations.RemoveField(
            model_name="rentdeal",
            name="external_id",
        ),
        migrations.RemoveField(
            model_name="rentdeal",
            name="external_hash",
        ),
        migrations.RemoveField(
            model_name="rentdeal",
            name="created_at",
        ),
        # ---- PK 교체: 기존 BigAutoField id 제거 후 CharField id 재추가 ----
        # Django는 단일 트랜잭션 내 PK 교체를 직접 지원하지 않으므로 RemoveField → AddField 패턴 사용.
        # DB 0행 가정이라 안전.
        migrations.RemoveField(
            model_name="rentdeal",
            name="id",
        ),
        migrations.AddField(
            model_name="rentdeal",
            name="id",
            field=models.CharField(
                primary_key=True,
                serialize=False,
                max_length=60,
                default="",
                help_text=(
                    "8자리 ldong + 1~2자 housing 코드 + YYMMDD + NNN, dash 없음. "
                    "예: 11010100A260514001"
                ),
            ),
            preserve_default=False,
        ),
        # ---- 컬럼 정합 ----
        # housing_type: NOT NULL + max_length 20 + choices 5종 한글.
        migrations.AlterField(
            model_name="rentdeal",
            name="housing_type",
            field=models.CharField(
                choices=HOUSING_TYPE_CHOICES_NEW,
                help_text="아파트, 연립다세대, 다가구, 단독, 오피스텔 (5종)",
                max_length=20,
            ),
        ),
        # deal_date → contract_date 이름 변경.
        migrations.RenameField(
            model_name="rentdeal",
            old_name="deal_date",
            new_name="contract_date",
        ),
        migrations.AlterField(
            model_name="rentdeal",
            name="contract_date",
            field=models.DateField(help_text="계약일 (NOT NULL)"),
        ),
        # build_year → construction_year 이름 변경.
        migrations.RenameField(
            model_name="rentdeal",
            old_name="build_year",
            new_name="construction_year",
        ),
        migrations.AlterField(
            model_name="rentdeal",
            name="construction_year",
            field=models.SmallIntegerField(
                blank=True,
                null=True,
                help_text="건축 연도. 응답 그대로 보존 (이상치 포함).",
            ),
        ),
        # area_m2: Float → Decimal.
        migrations.AlterField(
            model_name="rentdeal",
            name="area_m2",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="전용면적 ㎡. NULL 허용 (응답 결측 시 그대로 유지).",
                max_digits=12,
                null=True,
            ),
        ),
        # deposit: PositiveInteger → BigInteger NOT NULL.
        migrations.AlterField(
            model_name="rentdeal",
            name="deposit",
            field=models.BigIntegerField(help_text="보증금 (만원, NOT NULL)"),
        ),
        # monthly_rent: PositiveInteger → Integer NOT NULL.
        migrations.AlterField(
            model_name="rentdeal",
            name="monthly_rent",
            field=models.IntegerField(
                help_text="월세 (만원, NOT NULL). 0이면 전세."
            ),
        ),
        # previous_deposit / previous_monthly_rent: BigInteger/Integer nullable.
        migrations.AlterField(
            model_name="rentdeal",
            name="previous_deposit",
            field=models.BigIntegerField(
                blank=True,
                null=True,
                help_text="종전 계약 보증금 (만원)",
            ),
        ),
        migrations.AlterField(
            model_name="rentdeal",
            name="previous_monthly_rent",
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text="종전 계약 월세 (만원)",
            ),
        ),
        # contract_type max_length 20 유지, contract_end_date 유지.
        migrations.AlterField(
            model_name="rentdeal",
            name="contract_type",
            field=models.CharField(
                blank=True,
                help_text="신규, 갱신 (CHECK ck_rent_deal_contract_type, NULL 허용)",
                max_length=20,
            ),
        ),
        # house_name: varchar(200) → varchar(100).
        migrations.AlterField(
            model_name="rentdeal",
            name="house_name",
            field=models.CharField(blank=True, help_text="건물명", max_length=100),
        ),
        # jibun: varchar(64) → varchar(50).
        migrations.AlterField(
            model_name="rentdeal",
            name="jibun",
            field=models.CharField(
                blank=True,
                help_text="'법정동 + 지번' 원문",
                max_length=50,
            ),
        ),
        # ldong FK: NOT NULL.
        migrations.AlterField(
            model_name="rentdeal",
            name="ldong",
            field=models.ForeignKey(
                db_column="ldong_code",
                help_text="법정동 (NOT NULL, schema.dbml line 162).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="rent_deals",
                to="regions.ldong",
            ),
        ),
        # ---- 인덱스 재추가 ----
        migrations.AddIndex(
            model_name="rentdeal",
            index=models.Index(
                fields=["ldong", "contract_date"],
                name="rent_deal_ldong_contract_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="rentdeal",
            index=models.Index(
                fields=["housing_type", "contract_date"],
                name="rent_deal_htype_contract_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="rentdeal",
            index=models.Index(
                fields=["housing_type"],
                name="rent_deal_htype_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="rentdeal",
            index=django.contrib.postgres.indexes.GistIndex(
                fields=["location"], name="rentdeal_location_gist_idx"
            ),
        ),
        # ---- Meta options 갱신 (ordering 변경) ----
        migrations.AlterModelOptions(
            name="rentdeal",
            options={
                "ordering": ["-contract_date"],
                "verbose_name": "전월세 실거래",
                "verbose_name_plural": "전월세 실거래",
            },
        ),
    ]
