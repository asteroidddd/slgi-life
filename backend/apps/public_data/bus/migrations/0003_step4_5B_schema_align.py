"""sub-plan 4.5B — bus 앱 BusStop/BusCongestion 모델을 schema.dbml line 243~264 정합.

변경 요약 (DB 0행 가정):
- BusStop PK: BigAutoField → CharField(max_length=20).
- BusStop: dong FK (neighborhoods.Dong, to_field='code') 제거.
- BusStop: adong FK 신설 (regions.Adong, db_column='adong_code', nullable).
- BusStop: ldong FK 보존 (nullable).
- BusStop: arsId(varchar(10)) → stop_number(varchar(20)) 이름 변경 + 길이 정합.
- BusStop: external_id / created_at / updated_at 제거.
- BusCongestion: congestion NOT NULL (schema.dbml line 259).
- BusCongestion: congestion DecimalField max_digits 10 → 12.

state + database 둘 다 일관 적용. DB 0행 가정.
"""

import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bus", "0002_rename_geom_to_location"),
        ("regions", "0004_add_adong"),
    ]

    operations = [
        # ---- BusStop: 인덱스/FK 제거 단계 ----
        migrations.RemoveIndex(
            model_name="busstop",
            name="busstop_location_gist_idx",
        ),
        migrations.RemoveIndex(
            model_name="busstop",
            name="bus_stop_adong_c_711295_idx",
        ),
        migrations.RemoveIndex(
            model_name="busstop",
            name="bus_stop_ldong_c_33a3d6_idx",
        ),
        migrations.RemoveIndex(
            model_name="busstop",
            name="bus_stop_arsId_a3e096_idx",
        ),
        # legacy dong FK 제거.
        migrations.RemoveField(
            model_name="busstop",
            name="dong",
        ),
        migrations.RemoveField(
            model_name="busstop",
            name="external_id",
        ),
        migrations.RemoveField(
            model_name="busstop",
            name="created_at",
        ),
        migrations.RemoveField(
            model_name="busstop",
            name="updated_at",
        ),
        # arsId → stop_number 이름 변경 + max_length 갱신.
        migrations.RenameField(
            model_name="busstop",
            old_name="arsId",
            new_name="stop_number",
        ),
        migrations.AlterField(
            model_name="busstop",
            name="stop_number",
            field=models.CharField(
                blank=True,
                help_text="정류소번호 (서울 BIS arsId). RDS bus_stop.stop_number 1:1.",
                max_length=20,
            ),
        ),
        # ---- PK 교체: BigAutoField id → CharField id ----
        migrations.RemoveField(
            model_name="busstop",
            name="id",
        ),
        migrations.AddField(
            model_name="busstop",
            name="id",
            field=models.CharField(
                primary_key=True,
                serialize=False,
                max_length=20,
                default="",
                help_text="정류장 ID (RDS bus_stop.id, varchar(20)).",
            ),
            preserve_default=False,
        ),
        # name NOT NULL 유지, max_length 변경 없음.
        # adong FK 신설 (nullable).
        migrations.AddField(
            model_name="busstop",
            name="adong",
            field=models.ForeignKey(
                blank=True,
                db_column="adong_code",
                help_text="행정동 (nullable).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bus_stops",
                to="regions.adong",
            ),
        ),
        # ---- 인덱스 재추가 ----
        migrations.AddIndex(
            model_name="busstop",
            index=django.contrib.postgres.indexes.GistIndex(
                fields=["location"], name="busstop_location_gist_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="busstop",
            index=models.Index(
                fields=["adong"], name="bus_stop_adong_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="busstop",
            index=models.Index(
                fields=["ldong"], name="bus_stop_ldong_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="busstop",
            index=models.Index(
                fields=["stop_number"], name="bus_stop_stop_num_idx"
            ),
        ),
        # ---- BusCongestion 정합 ----
        # congestion: nullable → NOT NULL + max_digits 12.
        migrations.AlterField(
            model_name="buscongestion",
            name="congestion",
            field=models.DecimalField(
                decimal_places=4,
                help_text=(
                    "혼잡도 (RouteCongestionLevel API 응답값. 시간대·노선 평균. "
                    "단위는 응답 그대로, 보통 0~210). NOT NULL."
                ),
                max_digits=12,
            ),
        ),
    ]
