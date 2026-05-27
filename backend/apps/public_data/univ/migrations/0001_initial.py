"""sub-plan 2M — Univ / UnivAdong / UnivLdong 신설 (schema.dbml line 301~331).

state+database 둘 다 CreateModel × 3. fresh migrate 시 정상 적용.

변경 요약:
- Univ 신설: id varchar(5), name, school_type (CHECK 8종),
  boundary(multipolygon, 4326), location(point, 4326).
- UnivAdong 신설: regions.Adong FK 다대다, unique (univ, adong).
- UnivLdong 신설: regions.Ldong FK 다대다, unique (univ, ldong).
"""

import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("regions", "0004_add_adong"),
    ]

    operations = [
        migrations.CreateModel(
            name="Univ",
            fields=[
                (
                    "id",
                    models.CharField(
                        help_text=(
                            "type 1글자(U/C/I/E/B/P/V/M) + 001~999. "
                            "type별 가나다 정렬"
                        ),
                        max_length=5,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="OSM name 또는 사용자 보강",
                        max_length=200,
                    ),
                ),
                (
                    "school_type",
                    models.CharField(
                        choices=[
                            ("일반대학", "일반대학"),
                            ("전문대학", "전문대학"),
                            ("산업대학", "산업대학"),
                            ("교육대학", "교육대학"),
                            ("방송통신대학", "방송통신대학"),
                            ("기능대학", "기능대학"),
                            ("전공대학", "전공대학"),
                            ("각종대학(대학)", "각종대학(대학)"),
                        ],
                        help_text=(
                            "일반대학/전문대학/산업대학/교육대학/방송통신대학/"
                            "기능대학/전공대학/각종대학(대학) "
                            "(CHECK ck_univ_school_type 8종)"
                        ),
                        max_length=20,
                    ),
                ),
                (
                    "boundary",
                    django.contrib.gis.db.models.fields.MultiPolygonField(
                        help_text="대학 경계 (WGS84)",
                        srid=4326,
                    ),
                ),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        help_text="ST_PointOnSurface(boundary) (WGS84)",
                        srid=4326,
                    ),
                ),
            ],
            options={
                "verbose_name": "대학",
                "verbose_name_plural": "대학",
                "db_table": "univ",
                "ordering": ["id"],
                "indexes": [
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["boundary"], name="univ_boundary_gist_idx"
                    ),
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["location"], name="univ_location_gist_idx"
                    ),
                    models.Index(
                        fields=["school_type"], name="ix_univ_school_type"
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        check=models.Q(
                            school_type__in=[
                                "일반대학",
                                "전문대학",
                                "산업대학",
                                "교육대학",
                                "방송통신대학",
                                "기능대학",
                                "전공대학",
                                "각종대학(대학)",
                            ]
                        ),
                        name="ck_univ_school_type",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="UnivAdong",
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
                    "univ",
                    models.ForeignKey(
                        db_column="univ_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="adong_links",
                        to="univ.univ",
                    ),
                ),
                (
                    "adong",
                    models.ForeignKey(
                        db_column="adong_code",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="univ_links",
                        to="regions.adong",
                    ),
                ),
            ],
            options={
                "verbose_name": "대학 ↔ 행정동",
                "verbose_name_plural": "대학 ↔ 행정동",
                "db_table": "univ_adong",
                "indexes": [
                    models.Index(fields=["univ"], name="ix_univ_adong_univ"),
                    models.Index(fields=["adong"], name="ix_univ_adong_adong"),
                ],
                "unique_together": {("univ", "adong")},
            },
        ),
        migrations.CreateModel(
            name="UnivLdong",
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
                    "univ",
                    models.ForeignKey(
                        db_column="univ_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ldong_links",
                        to="univ.univ",
                    ),
                ),
                (
                    "ldong",
                    models.ForeignKey(
                        db_column="ldong_code",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="univ_links",
                        to="regions.ldong",
                    ),
                ),
            ],
            options={
                "verbose_name": "대학 ↔ 법정동",
                "verbose_name_plural": "대학 ↔ 법정동",
                "db_table": "univ_ldong",
                "indexes": [
                    models.Index(fields=["univ"], name="ix_univ_ldong_univ"),
                    models.Index(fields=["ldong"], name="ix_univ_ldong_ldong"),
                ],
                "unique_together": {("univ", "ldong")},
            },
        ),
    ]
