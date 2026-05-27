"""Sub-plan 2E — Store / BusinessCategory / KsciCategory 신설 (amenities에서 이동).

state + database CreateModel. fresh migrate 시 amenities/0004 (drop) 직후 실행되어
3 테이블을 재생성한다. 단계 5 docker fresh migrate 환경에서 SLGI DB는 데이터 0행
이므로 drop→recreate 비용은 무해.

컬럼 / 인덱스 / FK 구성은 amenities/0002 + 0003 누적 상태와 동일하다.
"""

import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("amenities", "0004_remove_store_models"),
        ("neighborhoods", "0002_alter_dong_code"),
        ("regions", "0003_remove_populations"),
    ]

    operations = [
        migrations.CreateModel(
            name="KsciCategory",
            fields=[
                (
                    "ksci_code",
                    models.CharField(
                        help_text="KSCI 코드 (RDS PK)",
                        max_length=20,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "subcategory_name",
                    models.CharField(blank=True, help_text="소분류명", max_length=200),
                ),
                ("class_name", models.CharField(blank=True, help_text="세분류명", max_length=200)),
                (
                    "subclass_name",
                    models.CharField(blank=True, help_text="세세분류명", max_length=200),
                ),
                (
                    "middle_category_name",
                    models.CharField(blank=True, help_text="중분류명", max_length=200),
                ),
                (
                    "main_category_name",
                    models.CharField(blank=True, help_text="대분류명", max_length=200),
                ),
            ],
            options={
                "verbose_name": "한국표준산업분류",
                "verbose_name_plural": "한국표준산업분류",
                "db_table": "ksci_category",
                "ordering": ["ksci_code"],
            },
        ),
        migrations.CreateModel(
            name="BusinessCategory",
            fields=[
                (
                    "subcategory_code",
                    models.CharField(
                        help_text="소분류 코드 (RDS PK)",
                        max_length=20,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "subcategory_name",
                    models.CharField(blank=True, help_text="소분류명", max_length=100),
                ),
                (
                    "middle_category_code",
                    models.CharField(blank=True, help_text="중분류 코드", max_length=20),
                ),
                (
                    "middle_category_name",
                    models.CharField(blank=True, help_text="중분류명", max_length=100),
                ),
                (
                    "main_category_code",
                    models.CharField(blank=True, help_text="대분류 코드", max_length=20),
                ),
                (
                    "main_category_name",
                    models.CharField(blank=True, help_text="대분류명", max_length=100),
                ),
            ],
            options={
                "verbose_name": "소상공인 카테고리",
                "verbose_name_plural": "소상공인 카테고리",
                "db_table": "business_category",
                "ordering": ["subcategory_code"],
                "indexes": [
                    models.Index(
                        fields=["middle_category_code"], name="business_ca_middle__106a60_idx"
                    ),
                    models.Index(
                        fields=["main_category_code"], name="business_ca_main_ca_6484ca_idx"
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Store",
            fields=[
                (
                    "id",
                    models.CharField(
                        help_text="상가 ID (RDS store.id)",
                        max_length=64,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(blank=True, help_text="상호명", max_length=300)),
                ("branch_name", models.CharField(blank=True, help_text="지점명", max_length=200)),
                ("address", models.CharField(blank=True, help_text="주소", max_length=500)),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True, help_text="상가 위치 (WGS84)", null=True, srid=4326
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        db_column="category_code",
                        help_text="소상공인 소분류 (RDS store.category_code → BusinessCategory.subcategory_code)",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stores",
                        to="store.businesscategory",
                    ),
                ),
                (
                    "dong",
                    models.ForeignKey(
                        blank=True,
                        db_column="adong_code",
                        help_text="행정동 (RDS adong_code → Dong.code)",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stores",
                        to="neighborhoods.dong",
                        to_field="code",
                    ),
                ),
                (
                    "ksci",
                    models.ForeignKey(
                        blank=True,
                        db_column="ksci_code",
                        help_text="한국표준산업분류 (RDS ksci_code)",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stores",
                        to="store.kscicategory",
                    ),
                ),
                (
                    "ldong",
                    models.ForeignKey(
                        blank=True,
                        db_column="ldong_code",
                        help_text="법정동 (RDS ldong_code)",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stores",
                        to="regions.ldong",
                    ),
                ),
            ],
            options={
                "verbose_name": "상가",
                "verbose_name_plural": "상가",
                "db_table": "store",
                "indexes": [
                    models.Index(fields=["dong"], name="store_adong_c_b8a0a4_idx"),
                    models.Index(fields=["ldong"], name="store_ldong_c_a49541_idx"),
                    models.Index(fields=["category"], name="store_categor_a63bc0_idx"),
                    models.Index(fields=["ksci"], name="store_ksci_co_e67d73_idx"),
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["location"], name="store_location_gist_idx"
                    ),
                ],
            },
        ),
    ]
