"""sub-plan 2J — Adong 모델 신설 (schema.dbml line 119~127).

기존 service.neighborhoods.Dong(=행정동, db_table='dong')은 그대로 유지하며,
본 Adong은 RDS `adong` 테이블 1:1 매핑 신설 모델이다. db_table='adong'.

state+database 둘 다 CreateModel. fresh migrate 시 정상 적용.
"""

import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0003_remove_populations"),
    ]

    operations = [
        migrations.CreateModel(
            name="Adong",
            fields=[
                (
                    "adong_code",
                    models.CharField(
                        help_text="행정동 코드 (RDS adong.adong_code)",
                        max_length=20,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="행정동 이름", max_length=100),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text=(
                            "URL용 고유 식별자. 패턴: <gu_name>-<name> "
                            "(예: 강남구-신사동)"
                        ),
                        max_length=80,
                        unique=True,
                    ),
                ),
                (
                    "area_m2",
                    models.DecimalField(
                        blank=True,
                        decimal_places=4,
                        help_text="면적 (m^2)",
                        max_digits=20,
                        null=True,
                    ),
                ),
                (
                    "boundary",
                    django.contrib.gis.db.models.fields.MultiPolygonField(
                        blank=True,
                        help_text="행정동 경계 (WGS84)",
                        null=True,
                        srid=4326,
                    ),
                ),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True,
                        help_text="중심점 (WGS84)",
                        null=True,
                        srid=4326,
                    ),
                ),
                (
                    "gu",
                    models.ForeignKey(
                        db_column="gu_code",
                        help_text="속한 자치구 (RDS adong.gu_code)",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="adongs",
                        to="regions.gu",
                    ),
                ),
            ],
            options={
                "verbose_name": "행정동",
                "verbose_name_plural": "행정동",
                "db_table": "adong",
                "ordering": ["adong_code"],
                "indexes": [
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["boundary"], name="adong_boundary_gist_idx"
                    ),
                ],
            },
        ),
    ]
