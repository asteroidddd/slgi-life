"""Sub-plan 2G — BusStop / BusCongestion 신설 (transit에서 이동).

state + database CreateModel. fresh migrate 시 transit/0005 (drop) 직후 실행되어
2 테이블을 재생성한다. 단계 5 docker fresh migrate 환경에서 SLGI DB는 데이터 0행
이므로 drop→recreate 비용은 무해.

컬럼 / 인덱스 / FK 구성은 transit/0001 + 0002 + 0003 누적 상태와 동일하다.
- BusStop: external_id unique, dong/ldong nullable FK, geom GiST(nullable), arsId Index.
- BusCongestion: bus_stop FK, (bus_stop, date, time) unique, BRIN(date), (bus_stop, -date) Index.
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
            name="BusStop",
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
                        help_text="RDS bus_stop.id (Phase 1 신규). RDS PK 1:1.",
                        max_length=32,
                        null=True,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(help_text="정류장 명칭", max_length=100)),
                (
                    "arsId",
                    models.CharField(
                        blank=True,
                        help_text="정류소번호 (서울 BIS arsId). RDS stop_number 1:1.",
                        max_length=10,
                    ),
                ),
                (
                    "geom",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True,
                        help_text="정류장 위치 (WGS84). GiST 인덱스. RDS에 NULL 719건 존재.",
                        null=True,
                        srid=4326,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dong",
                    models.ForeignKey(
                        blank=True,
                        db_column="adong_code",
                        help_text="행정동 (Phase 1: nullable로 완화. RDS 95% 매핑, 5%는 좌표 보강).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="bus_stops",
                        to="neighborhoods.dong",
                        to_field="code",
                    ),
                ),
                (
                    "ldong",
                    models.ForeignKey(
                        blank=True,
                        db_column="ldong_code",
                        help_text="법정동 (Phase 1 신규, RDS ldong_code).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="bus_stops",
                        to="regions.ldong",
                    ),
                ),
            ],
            options={
                "verbose_name": "버스 정류장",
                "verbose_name_plural": "버스 정류장",
                "db_table": "bus_stop",
                "indexes": [
                    models.Index(fields=["dong"], name="bus_stop_adong_c_711295_idx"),
                    models.Index(fields=["ldong"], name="bus_stop_ldong_c_33a3d6_idx"),
                    models.Index(fields=["arsId"], name="bus_stop_arsId_a3e096_idx"),
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["geom"], name="busstop_geom_gist_idx"
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="BusCongestion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("date", models.DateField(help_text="기준일")),
                ("time", models.TimeField(help_text="시간대")),
                (
                    "congestion",
                    models.DecimalField(
                        blank=True, decimal_places=4, help_text="혼잡도", max_digits=10, null=True
                    ),
                ),
                (
                    "bus_stop",
                    models.ForeignKey(
                        db_column="bus_stop_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="congestions",
                        to="bus.busstop",
                    ),
                ),
            ],
            options={
                "verbose_name": "버스 혼잡도",
                "verbose_name_plural": "버스 혼잡도",
                "db_table": "bus_congestion",
                "indexes": [
                    django.contrib.postgres.indexes.BrinIndex(
                        fields=["date"], name="buscongestion_date_brin_idx"
                    ),
                    models.Index(
                        fields=["bus_stop", "-date"], name="bus_congest_bus_sto_c2984d_idx"
                    ),
                ],
                "unique_together": {("bus_stop", "date", "time")},
            },
        ),
    ]
