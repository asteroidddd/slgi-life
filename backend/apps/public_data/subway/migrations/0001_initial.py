"""Sub-plan 2F — SubwayStation / NearestSubway / SubwayCongestion 신설 (transit에서 이동).

state + database CreateModel. fresh migrate 시 transit/0004 (drop) 직후 실행되어
3 테이블을 재생성한다. 단계 5 docker fresh migrate 환경에서 SLGI DB는 데이터 0행
이므로 drop→recreate 비용은 무해.

컬럼 / 인덱스 / FK 구성은 transit/0001 + 0002 누적 상태와 동일하다.
- SubwayStation: external_id unique, dong/ldong nullable FK, geom GiST.
- NearestSubway: dong/station FK, (dong, rank) unique.
- SubwayCongestion: station FK, (station, day_type, direction, express_yn, time) unique.
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
            name="SubwayStation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(help_text="역명 (예: '충무로')", max_length=50)),
                ("line", models.CharField(help_text="노선 (예: '3호선')", max_length=20)),
                (
                    "external_id",
                    models.CharField(
                        blank=True,
                        help_text="RDS subway_station.id (Phase 1: unique 제약).",
                        max_length=32,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "geom",
                    django.contrib.gis.db.models.fields.PointField(
                        help_text="역 위치 (WGS84). GiST 인덱스.", srid=4326
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dong",
                    models.ForeignKey(
                        blank=True,
                        db_column="adong_code",
                        help_text="행정동 (Phase 1 신규, RDS adong_code).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="subway_stations",
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
                        related_name="subway_stations",
                        to="regions.ldong",
                    ),
                ),
            ],
            options={
                "verbose_name": "지하철역",
                "verbose_name_plural": "지하철역",
                "db_table": "subway_station",
                "ordering": ["line", "name"],
                "indexes": [
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["geom"], name="subway_geom_gist_idx"
                    ),
                    models.Index(fields=["dong"], name="subway_stat_adong_c_77e870_idx"),
                    models.Index(fields=["ldong"], name="subway_stat_ldong_c_9e7181_idx"),
                ],
                "unique_together": {("name", "line")},
            },
        ),
        migrations.CreateModel(
            name="NearestSubway",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("rank", models.PositiveSmallIntegerField(help_text="1~3")),
                ("distance_m", models.FloatField(help_text="동 centroid → 역 직선 거리 (m)")),
                (
                    "dong",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nearest_subways",
                        to="neighborhoods.dong",
                    ),
                ),
                (
                    "station",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dong_rankings",
                        to="subway.subwaystation",
                    ),
                ),
            ],
            options={
                "verbose_name": "가까운 지하철역 (사전계산)",
                "verbose_name_plural": "가까운 지하철역 (사전계산)",
                "db_table": "nearest_subway",
                "ordering": ["dong", "rank"],
                "unique_together": {("dong", "rank")},
            },
        ),
        migrations.CreateModel(
            name="SubwayCongestion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("day_type", models.CharField(help_text="평일/토요일/일요일", max_length=10)),
                ("direction", models.CharField(help_text="상선/하선", max_length=10)),
                ("express_yn", models.CharField(help_text="일반/급행", max_length=10)),
                ("time", models.TimeField(help_text="시간대")),
                (
                    "congestion",
                    models.DecimalField(
                        decimal_places=4, help_text="혼잡도 (numeric NOT NULL)", max_digits=10
                    ),
                ),
                (
                    "station",
                    models.ForeignKey(
                        db_column="station_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="congestions",
                        to="subway.subwaystation",
                    ),
                ),
            ],
            options={
                "verbose_name": "지하철 혼잡도",
                "verbose_name_plural": "지하철 혼잡도",
                "db_table": "subway_congestion",
                "indexes": [
                    models.Index(
                        fields=["station", "day_type"], name="subway_cong_station_43fb82_idx"
                    ),
                    models.Index(
                        fields=["day_type", "time"], name="subway_cong_day_typ_f2d5b8_idx"
                    ),
                ],
                "unique_together": {("station", "day_type", "direction", "express_yn", "time")},
            },
        ),
    ]
