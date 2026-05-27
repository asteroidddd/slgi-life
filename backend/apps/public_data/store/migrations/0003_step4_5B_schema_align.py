"""sub-plan 4.5B — store 앱 Store 모델을 schema.dbml line 181~196 정합.

변경 요약 (DB 0행 가정):
- Store PK: varchar(64) → varchar(50). 'id varchar(50)'.
- Store.name: blank=True → NOT NULL (max_length 300 → 100).
- Store.branch_name: max_length 200 → 100.
- Store.category: nullable → NOT NULL FK.
- Store.ksci: nullable 허용 유지 (schema.dbml ksci_code NULL 허용).
- Store.dong FK (neighborhoods.Dong) 제거.
- Store.adong FK 신설 (regions.Adong, db_column='adong_code', NOT NULL).
- Store.ldong FK: nullable → NOT NULL.
- Store.address: blank=True → NOT NULL, max_length 500 → 255.
- Store.location: nullable → NOT NULL.

BusinessCategory / KsciCategory는 sub-plan 4.5A에서 정합 완료. 본 sub-plan에서 추가 변경 없음.

state + database 둘 다 일관 적용. DB 0행 가정.
"""

import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0002_step4_5A_category_not_null"),
        ("regions", "0004_add_adong"),
    ]

    operations = [
        # ---- 인덱스/FK 제거 단계 ----
        migrations.RemoveIndex(
            model_name="store",
            name="store_location_gist_idx",
        ),
        migrations.RemoveIndex(
            model_name="store",
            name="store_adong_c_b8a0a4_idx",
        ),
        migrations.RemoveIndex(
            model_name="store",
            name="store_ldong_c_a49541_idx",
        ),
        migrations.RemoveIndex(
            model_name="store",
            name="store_categor_a63bc0_idx",
        ),
        migrations.RemoveIndex(
            model_name="store",
            name="store_ksci_co_e67d73_idx",
        ),
        # legacy dong FK (neighborhoods.Dong, to_field='code') 제거.
        migrations.RemoveField(
            model_name="store",
            name="dong",
        ),
        # ---- PK 길이 정합: varchar(64) → varchar(50) ----
        migrations.AlterField(
            model_name="store",
            name="id",
            field=models.CharField(
                help_text="상가 ID (RDS store.id, varchar(50))",
                max_length=50,
                primary_key=True,
                serialize=False,
            ),
        ),
        # ---- name: NOT NULL + max_length 100 ----
        migrations.AlterField(
            model_name="store",
            name="name",
            field=models.CharField(help_text="상호명 (NOT NULL)", max_length=100),
        ),
        # ---- branch_name: max_length 100 ----
        migrations.AlterField(
            model_name="store",
            name="branch_name",
            field=models.CharField(blank=True, help_text="지점명", max_length=100),
        ),
        # ---- category: NOT NULL ----
        migrations.AlterField(
            model_name="store",
            name="category",
            field=models.ForeignKey(
                db_column="category_code",
                help_text="소상공인 소분류 (schema.dbml NOT NULL).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="stores",
                to="store.businesscategory",
            ),
        ),
        # ---- ksci: nullable 유지 (schema.dbml line 186) ----
        migrations.AlterField(
            model_name="store",
            name="ksci",
            field=models.ForeignKey(
                blank=True,
                db_column="ksci_code",
                help_text="한국표준산업분류 (API 응답 결측 시 NULL 허용).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="stores",
                to="store.kscicategory",
            ),
        ),
        # ---- adong FK 신설 (NOT NULL) ----
        migrations.AddField(
            model_name="store",
            name="adong",
            field=models.ForeignKey(
                db_column="adong_code",
                help_text="행정동 (schema.dbml NOT NULL).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="stores",
                to="regions.adong",
            ),
        ),
        # ---- ldong: nullable → NOT NULL ----
        migrations.AlterField(
            model_name="store",
            name="ldong",
            field=models.ForeignKey(
                db_column="ldong_code",
                help_text="법정동 (schema.dbml NOT NULL).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="stores",
                to="regions.ldong",
            ),
        ),
        # ---- address: NOT NULL + max_length 255 ----
        migrations.AlterField(
            model_name="store",
            name="address",
            field=models.CharField(help_text="주소 (NOT NULL)", max_length=255),
        ),
        # ---- location: NOT NULL ----
        migrations.AlterField(
            model_name="store",
            name="location",
            field=django.contrib.gis.db.models.fields.PointField(
                help_text="상가 위치 (WGS84, schema.dbml NOT NULL).", srid=4326
            ),
        ),
        # ---- 인덱스 재추가 ----
        migrations.AddIndex(
            model_name="store",
            index=django.contrib.postgres.indexes.GistIndex(
                fields=["location"], name="store_location_gist_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="store",
            index=models.Index(fields=["adong"], name="store_adong_idx"),
        ),
        migrations.AddIndex(
            model_name="store",
            index=models.Index(fields=["ldong"], name="store_ldong_idx"),
        ),
        migrations.AddIndex(
            model_name="store",
            index=models.Index(fields=["category"], name="store_category_idx"),
        ),
        migrations.AddIndex(
            model_name="store",
            index=models.Index(fields=["ksci"], name="store_ksci_idx"),
        ),
    ]
