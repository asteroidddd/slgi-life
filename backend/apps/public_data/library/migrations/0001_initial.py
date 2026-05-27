"""sub-plan 2N — Library / LibraryHours 신설 (schema.dbml line 333~358).

state+database 둘 다 CreateModel × 2. fresh migrate 시 정상 적용.

변경 요약:
- Library 신설: id varchar(20), name, library_type (CHECK 2종),
  remark(NULL 허용), location(point, 4326), ldong/adong FK.
- LibraryHours 신설: library FK, day_type (CHECK 7종),
  time_open/time_close, is_irregular, unique (library, day_type).
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
            name="Library",
            fields=[
                (
                    "id",
                    models.CharField(
                        help_text=(
                            "Seoul Open API LBRRY_SEQ_NO 그대로. "
                            "공공/작은 두 endpoint 사이 중복 0 검증됨"
                        ),
                        max_length=20,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text=(
                            "LBRRY_NAME 그대로. "
                            "폐관 [폐관]/[페관] 접두사 42건은 적재 대상 외"
                        ),
                        max_length=100,
                    ),
                ),
                (
                    "library_type",
                    models.CharField(
                        choices=[
                            ("공공도서관", "공공도서관"),
                            ("작은도서관", "작은도서관"),
                        ],
                        help_text=(
                            "공공도서관/작은도서관 "
                            "(LBRRY_SE_NAME, CHECK ck_library_library_type 2종)"
                        ),
                        max_length=20,
                    ),
                ),
                (
                    "remark",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "비정형 운영 정보 통합. 시즌 변동/점심 분리/N째주/"
                            "N·M주/부분실/리모델링/휴관중/특정 휴일 등의 자유 텍스트. "
                            "표준 운영 시 NULL"
                        ),
                        null=True,
                    ),
                ),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        help_text=(
                            "ST_SetSRID(ST_MakePoint(YDNTS, XCNTS), 4326) — "
                            "XCNTS=lat / YDNTS=lon (실측 lock)"
                        ),
                        srid=4326,
                    ),
                ),
                (
                    "ldong",
                    models.ForeignKey(
                        db_column="ldong_code",
                        help_text=(
                            "ST_Within(location, ldong.boundary). "
                            "다중 매칭 시 면적 최소"
                        ),
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="libraries",
                        to="regions.ldong",
                    ),
                ),
                (
                    "adong",
                    models.ForeignKey(
                        db_column="adong_code",
                        help_text=(
                            "ST_Within(location, adong.boundary). "
                            "다중 매칭 시 면적 최소"
                        ),
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="libraries",
                        to="regions.adong",
                    ),
                ),
            ],
            options={
                "verbose_name": "도서관",
                "verbose_name_plural": "도서관",
                "db_table": "library",
                "ordering": ["id"],
                "indexes": [
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["location"], name="library_location_gist_idx"
                    ),
                    models.Index(
                        fields=["library_type"], name="ix_library_library_type"
                    ),
                    models.Index(fields=["ldong"], name="ix_library_ldong"),
                    models.Index(fields=["adong"], name="ix_library_adong"),
                ],
                "constraints": [
                    models.CheckConstraint(
                        check=models.Q(
                            library_type__in=["공공도서관", "작은도서관"]
                        ),
                        name="ck_library_library_type",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="LibraryHours",
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
                    "library",
                    models.ForeignKey(
                        db_column="library_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hours",
                        to="library.library",
                    ),
                ),
                (
                    "day_type",
                    models.CharField(
                        choices=[
                            ("MON", "월"),
                            ("TUE", "화"),
                            ("WED", "수"),
                            ("THU", "목"),
                            ("FRI", "금"),
                            ("SAT", "토"),
                            ("SUN", "일"),
                        ],
                        help_text=(
                            "MON/TUE/WED/THU/FRI/SAT/SUN "
                            "(CHECK ck_library_hours_day_type 7종)"
                        ),
                        max_length=10,
                    ),
                ),
                (
                    "time_open",
                    models.TimeField(help_text="개관 시각"),
                ),
                (
                    "time_close",
                    models.TimeField(help_text="폐관 시각"),
                ),
                (
                    "is_irregular",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "요일 단위 불규칙 표시. "
                            "시즌 변동/점심 분리/N째주 등 비정형 적용 시 true"
                        ),
                    ),
                ),
            ],
            options={
                "verbose_name": "도서관 운영 시간",
                "verbose_name_plural": "도서관 운영 시간",
                "db_table": "library_hours",
                "indexes": [
                    models.Index(
                        fields=["library"], name="ix_library_hours_library"
                    ),
                    models.Index(
                        fields=["day_type"], name="ix_library_hours_day_type"
                    ),
                ],
                "unique_together": {("library", "day_type")},
                "constraints": [
                    models.CheckConstraint(
                        check=models.Q(
                            day_type__in=[
                                "MON",
                                "TUE",
                                "WED",
                                "THU",
                                "FRI",
                                "SAT",
                                "SUN",
                            ]
                        ),
                        name="ck_library_hours_day_type",
                    ),
                ],
            },
        ),
    ]
