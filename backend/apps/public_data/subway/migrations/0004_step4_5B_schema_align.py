"""sub-plan 4.5B — subway 앱 SubwayStation/SubwayCongestion 모델을 schema.dbml line 216~242 정합.

변경 요약 (DB 0행 가정):
- SubwayStation PK: BigAutoField → CharField(max_length=20).
- SubwayStation: dong FK (neighborhoods.Dong, to_field='code') 제거.
- SubwayStation: adong FK 신설 (regions.Adong, db_column='adong_code', NOT NULL).
- SubwayStation: ldong FK NOT NULL (기존 nullable → schema.dbml NOT NULL).
- SubwayStation: external_id / created_at / updated_at 제거.
- SubwayStation: unique_together (name, line) 제거 (schema.dbml에 없음).
- name max_length 50 → 100.
- SubwayCongestion: day_type/direction varchar(10) → varchar(20).
- SubwayCongestion: congestion DecimalField max_digits 10 → 12.
- NearestSubway (legacy, neighborhoods.Dong FK)는 보존 (lock D).
  station FK는 자동으로 varchar(20)로 cast됨.

state + database 둘 다 일관 적용. DB 0행 가정.
"""

import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subway", "0003_nearest_subway_v2"),
        ("regions", "0004_add_adong"),
    ]

    operations = [
        # ---- SubwayStation: 인덱스/FK 제거 단계 ----
        migrations.RemoveIndex(
            model_name="subwaystation",
            name="subway_location_gist_idx",
        ),
        migrations.RemoveIndex(
            model_name="subwaystation",
            name="subway_stat_adong_c_77e870_idx",
        ),
        migrations.RemoveIndex(
            model_name="subwaystation",
            name="subway_stat_ldong_c_9e7181_idx",
        ),
        migrations.AlterUniqueTogether(
            name="subwaystation",
            unique_together=set(),
        ),
        # legacy dong FK (neighborhoods.Dong, to_field='code') 제거.
        migrations.RemoveField(
            model_name="subwaystation",
            name="dong",
        ),
        # external_id / created_at / updated_at 제거.
        migrations.RemoveField(
            model_name="subwaystation",
            name="external_id",
        ),
        migrations.RemoveField(
            model_name="subwaystation",
            name="created_at",
        ),
        migrations.RemoveField(
            model_name="subwaystation",
            name="updated_at",
        ),
        # ldong FK는 일단 RemoveField 후 NOT NULL로 재추가.
        migrations.RemoveField(
            model_name="subwaystation",
            name="ldong",
        ),
        # ---- PK 교체: BigAutoField id → CharField id ----
        migrations.RemoveField(
            model_name="subwaystation",
            name="id",
        ),
        migrations.AddField(
            model_name="subwaystation",
            name="id",
            field=models.CharField(
                primary_key=True,
                serialize=False,
                max_length=20,
                default="",
                help_text="역 ID (RDS subway_station.id, varchar(20)).",
            ),
            preserve_default=False,
        ),
        # name max_length 50 → 100.
        migrations.AlterField(
            model_name="subwaystation",
            name="name",
            field=models.CharField(help_text="역명 (예: '충무로')", max_length=100),
        ),
        # adong FK 신설 (NOT NULL).
        migrations.AddField(
            model_name="subwaystation",
            name="adong",
            field=models.ForeignKey(
                db_column="adong_code",
                help_text="행정동 (schema.dbml NOT NULL).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subway_stations",
                to="regions.adong",
            ),
        ),
        # ldong FK 재추가 (NOT NULL).
        migrations.AddField(
            model_name="subwaystation",
            name="ldong",
            field=models.ForeignKey(
                db_column="ldong_code",
                help_text="법정동 (schema.dbml NOT NULL, M-1 lock).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subway_stations",
                to="regions.ldong",
            ),
        ),
        # ---- 인덱스 재추가 ----
        migrations.AddIndex(
            model_name="subwaystation",
            index=django.contrib.postgres.indexes.GistIndex(
                fields=["location"], name="subway_location_gist_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="subwaystation",
            index=models.Index(
                fields=["adong"], name="subway_stat_adong_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="subwaystation",
            index=models.Index(
                fields=["ldong"], name="subway_stat_ldong_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="subwaystation",
            index=models.Index(
                fields=["name"], name="subway_stat_name_idx"
            ),
        ),
        # ---- SubwayCongestion 정합 ----
        migrations.AlterField(
            model_name="subwaycongestion",
            name="day_type",
            field=models.CharField(
                help_text="평일/토요일/일요일/휴일 (CHECK ck_subway_congestion_day_type 4종)",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="subwaycongestion",
            name="direction",
            field=models.CharField(
                help_text="상선/하선/내선/외선 (CHECK ck_subway_congestion_direction 4종)",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="subwaycongestion",
            name="congestion",
            field=models.DecimalField(
                decimal_places=4,
                help_text="혼잡도 % (서울교통공사 기준 100=정원, 0~200+ 가능)",
                max_digits=12,
            ),
        ),
    ]
