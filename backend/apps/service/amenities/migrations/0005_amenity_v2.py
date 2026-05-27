"""sub-plan 2J — Amenity 모델 재구성 + AmenityAdong/AmenityLdong 신설.

schema.dbml line 365~400 정합. 변경 요약:
- category: 11종 → 17종 (CATEGORY_CHOICES), max_length 20 → 30
- geom → location (rename) + GistIndex name 갱신
- external_id → source_id (rename) + NOT NULL 강화 + unique 단독 제약 제거
- source → source_table (rename) + max_length 20 → 30 + choices 6종 갱신
- dong FK 제거 (Dong 1:1 → N:M)
- UniqueConstraint uq_amenity_source(source_table, source_id) 추가
- AmenityAdong / AmenityLdong 신설 (regions.Adong / regions.Ldong FK)

state+database 둘 다. fresh migrate 시 정상 적용.
"""

import django.db.models.deletion
from django.contrib.gis.db.models.fields import PointField
from django.contrib.postgres.indexes import GistIndex
from django.db import migrations, models


CATEGORY_CHOICES_NEW = [
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

SOURCE_TABLE_CHOICES_NEW = [
    ("store", "store"),
    ("park", "park"),
    ("library", "library"),
    ("univ", "univ"),
    ("subway_station", "subway_station"),
    ("bus_stop", "bus_stop"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("amenities", "0004_remove_store_models"),
        ("regions", "0004_add_adong"),
    ]

    operations = [
        # 1. dong FK 제거 (Dong 1:1 → AmenityAdong/AmenityLdong N:M).
        #    기존 amenity_dong_id_7a8d1d_idx (composite "dong, category")는
        #    RemoveField 시 자동 drop.
        migrations.RemoveField(
            model_name="amenity",
            name="dong",
        ),
        # 2. category: 17종 + max_length 30.
        migrations.AlterField(
            model_name="amenity",
            name="category",
            field=models.CharField(
                choices=CATEGORY_CHOICES_NEW,
                help_text="시설 카테고리 (17종, ck_amenity_category)",
                max_length=30,
            ),
        ),
        # 3. geom → location (rename) + GistIndex name 갱신.
        migrations.RemoveIndex(
            model_name="amenity",
            name="amenity_geom_gist_idx",
        ),
        migrations.RenameField(
            model_name="amenity",
            old_name="geom",
            new_name="location",
        ),
        migrations.AlterField(
            model_name="amenity",
            name="location",
            field=PointField(
                help_text="시설 위치 (WGS84). GiST 인덱스.",
                srid=4326,
            ),
        ),
        migrations.AddIndex(
            model_name="amenity",
            index=GistIndex(
                fields=["location"], name="amenity_location_gist_idx"
            ),
        ),
        # 4. external_id → source_id (rename) + NOT NULL 강화 + unique 단독 제거.
        migrations.RenameField(
            model_name="amenity",
            old_name="external_id",
            new_name="source_id",
        ),
        migrations.AlterField(
            model_name="amenity",
            name="source_id",
            field=models.CharField(
                help_text=(
                    "원천 PK 값 그대로. store.id / park.id / library.id / "
                    "univ.id / subway_station.id / bus_stop.id"
                ),
                max_length=64,
            ),
        ),
        # 5. source → source_table (rename) + max_length 30 + 6종 choices.
        migrations.RenameField(
            model_name="amenity",
            old_name="source",
            new_name="source_table",
        ),
        migrations.AlterField(
            model_name="amenity",
            name="source_table",
            field=models.CharField(
                choices=SOURCE_TABLE_CHOICES_NEW,
                help_text="원천 테이블명 (6종, ck_amenity_source_table)",
                max_length=30,
            ),
        ),
        # 6. UniqueConstraint uq_amenity_source(source_table, source_id).
        migrations.AddConstraint(
            model_name="amenity",
            constraint=models.UniqueConstraint(
                fields=["source_table", "source_id"], name="uq_amenity_source"
            ),
        ),
        # 7. AmenityAdong 신설.
        migrations.CreateModel(
            name="AmenityAdong",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "amenity",
                    models.ForeignKey(
                        db_column="amenity_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="adong_links",
                        to="amenities.amenity",
                    ),
                ),
                (
                    "adong",
                    models.ForeignKey(
                        db_column="adong_code",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="amenity_links",
                        to="regions.adong",
                    ),
                ),
            ],
            options={
                "verbose_name": "생활시설 ↔ 행정동",
                "verbose_name_plural": "생활시설 ↔ 행정동",
                "db_table": "amenity_adong",
                "indexes": [
                    models.Index(
                        fields=["amenity"],
                        name="amenity_ado_amenity_idx",
                    ),
                    models.Index(
                        fields=["adong"],
                        name="amenity_ado_adong_c_idx",
                    ),
                ],
                "unique_together": {("amenity", "adong")},
            },
        ),
        # 8. AmenityLdong 신설.
        migrations.CreateModel(
            name="AmenityLdong",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "amenity",
                    models.ForeignKey(
                        db_column="amenity_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ldong_links",
                        to="amenities.amenity",
                    ),
                ),
                (
                    "ldong",
                    models.ForeignKey(
                        db_column="ldong_code",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="amenity_links",
                        to="regions.ldong",
                    ),
                ),
            ],
            options={
                "verbose_name": "생활시설 ↔ 법정동",
                "verbose_name_plural": "생활시설 ↔ 법정동",
                "db_table": "amenity_ldong",
                "indexes": [
                    models.Index(
                        fields=["amenity"],
                        name="amenity_ldo_amenity_idx",
                    ),
                    models.Index(
                        fields=["ldong"],
                        name="amenity_ldo_ldong_c_idx",
                    ),
                ],
                "unique_together": {("amenity", "ldong")},
            },
        ),
    ]
