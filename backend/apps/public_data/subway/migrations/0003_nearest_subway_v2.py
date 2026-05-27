"""sub-plan 2L — NearestSubwayAdong / NearestSubwayLdong 신설.

schema.dbml line 449~473 정합. 변경 요약:
- NearestSubwayAdong 신설 (regions.Adong FK, rank 1~3, station_name 비정규화, distance_m)
- NearestSubwayLdong 신설 (regions.Ldong FK, rank 1~3, station_name 비정규화, distance_m)
- 기존 NearestSubway(legacy, neighborhoods.Dong FK)는 보존 (sub-plan 2O에서 drop 예정).

state+database 둘 다 CreateModel. fresh migrate 시 정상 적용.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subway", "0002_rename_geom_to_location"),
        ("regions", "0004_add_adong"),
    ]

    operations = [
        migrations.CreateModel(
            name="NearestSubwayAdong",
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
                ("rank", models.SmallIntegerField(help_text="1~3")),
                (
                    "station_name",
                    models.CharField(
                        help_text="지하철역 이름 (비정규화)", max_length=100
                    ),
                ),
                ("distance_m", models.FloatField(help_text="측지선 m (>= 0)")),
                (
                    "adong",
                    models.ForeignKey(
                        db_column="adong_code",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nearest_subways",
                        to="regions.adong",
                    ),
                ),
            ],
            options={
                "verbose_name": "가까운 지하철역 (행정동, 사전계산)",
                "verbose_name_plural": "가까운 지하철역 (행정동, 사전계산)",
                "db_table": "nearest_subway_adong",
                "ordering": ["adong", "rank"],
                "indexes": [
                    models.Index(
                        fields=["station_name"],
                        name="ix_nearest_subway_adong_name",
                    ),
                ],
                "unique_together": {("adong", "rank")},
            },
        ),
        migrations.CreateModel(
            name="NearestSubwayLdong",
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
                ("rank", models.SmallIntegerField(help_text="1~3")),
                (
                    "station_name",
                    models.CharField(
                        help_text="지하철역 이름 (비정규화)", max_length=100
                    ),
                ),
                ("distance_m", models.FloatField(help_text="측지선 m (>= 0)")),
                (
                    "ldong",
                    models.ForeignKey(
                        db_column="ldong_code",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nearest_subways",
                        to="regions.ldong",
                    ),
                ),
            ],
            options={
                "verbose_name": "가까운 지하철역 (법정동, 사전계산)",
                "verbose_name_plural": "가까운 지하철역 (법정동, 사전계산)",
                "db_table": "nearest_subway_ldong",
                "ordering": ["ldong", "rank"],
                "indexes": [
                    models.Index(
                        fields=["station_name"],
                        name="ix_nearest_subway_ldong_name",
                    ),
                ],
                "unique_together": {("ldong", "rank")},
            },
        ),
        migrations.AddConstraint(
            model_name="nearestsubwayadong",
            constraint=models.CheckConstraint(
                check=models.Q(("rank__gte", 1), ("rank__lte", 3)),
                name="ck_nearest_subway_adong_rank",
            ),
        ),
        migrations.AddConstraint(
            model_name="nearestsubwayadong",
            constraint=models.CheckConstraint(
                check=models.Q(("distance_m__gte", 0)),
                name="ck_nearest_subway_adong_distance",
            ),
        ),
        migrations.AddConstraint(
            model_name="nearestsubwayldong",
            constraint=models.CheckConstraint(
                check=models.Q(("rank__gte", 1), ("rank__lte", 3)),
                name="ck_nearest_subway_ldong_rank",
            ),
        ),
        migrations.AddConstraint(
            model_name="nearestsubwayldong",
            constraint=models.CheckConstraint(
                check=models.Q(("distance_m__gte", 0)),
                name="ck_nearest_subway_ldong_distance",
            ),
        ),
    ]
