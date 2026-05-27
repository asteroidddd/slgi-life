"""sub-plan 2K — CurrentSeoul/Gu/Ldong/Adong 4 모델 신설 (schema.dbml line 407~441).

단위(seoul / gu / ldong / adong)별 최신 score 캐시. 빈 테이블 신설.
데이터 적재는 별도 phase (DECISIONS O 섹션).

state+database 둘 다 CreateModel + CHECK constraints.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("regions", "0004_add_adong"),
    ]

    operations = [
        migrations.CreateModel(
            name="CurrentSeoul",
            fields=[
                (
                    "seoul",
                    models.OneToOneField(
                        db_column="code",
                        help_text="서울시 코드 (RDS current_seoul.code)",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="current_score",
                        serialize=False,
                        to="regions.seoul",
                    ),
                ),
                (
                    "score_rent",
                    models.FloatField(
                        blank=True,
                        help_text="최근 1년 환산월세/㎡ 기반 score. 거래 0 단위는 NULL",
                        null=True,
                    ),
                ),
                (
                    "score_amenity",
                    models.FloatField(help_text="생활/의료/공원 가중합 0~100"),
                ),
                (
                    "score_transit",
                    models.FloatField(
                        help_text=(
                            "지하철 1km anchor + 버스 면적당 밀도 p95 가중합 0~100"
                        )
                    ),
                ),
            ],
            options={
                "verbose_name": "서울 최신 score",
                "verbose_name_plural": "서울 최신 score",
                "db_table": "current_seoul",
            },
        ),
        migrations.CreateModel(
            name="CurrentGu",
            fields=[
                (
                    "gu",
                    models.OneToOneField(
                        db_column="gu_code",
                        help_text="자치구 코드 (RDS current_gu.gu_code)",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="current_score",
                        serialize=False,
                        to="regions.gu",
                    ),
                ),
                (
                    "score_rent",
                    models.FloatField(
                        blank=True,
                        help_text="최근 1년 환산월세/㎡ 기반 score. 거래 0 단위는 NULL",
                        null=True,
                    ),
                ),
                (
                    "score_amenity",
                    models.FloatField(help_text="생활/의료/공원 가중합 0~100"),
                ),
                (
                    "score_transit",
                    models.FloatField(
                        help_text=(
                            "지하철 1km anchor + 버스 면적당 밀도 p95 가중합 0~100"
                        )
                    ),
                ),
            ],
            options={
                "verbose_name": "자치구 최신 score",
                "verbose_name_plural": "자치구 최신 score",
                "db_table": "current_gu",
            },
        ),
        migrations.CreateModel(
            name="CurrentLdong",
            fields=[
                (
                    "ldong",
                    models.OneToOneField(
                        db_column="ldong_code",
                        help_text="법정동 코드 (RDS current_ldong.ldong_code)",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="current_score",
                        serialize=False,
                        to="regions.ldong",
                    ),
                ),
                (
                    "score_rent",
                    models.FloatField(
                        blank=True,
                        help_text="최근 1년 환산월세/㎡ 기반 score. 거래 0 동은 NULL",
                        null=True,
                    ),
                ),
                (
                    "score_amenity",
                    models.FloatField(help_text="생활/의료/공원 가중합 0~100"),
                ),
                (
                    "score_transit",
                    models.FloatField(
                        help_text=(
                            "지하철 1km anchor + 버스 면적당 밀도 p95 가중합 0~100"
                        )
                    ),
                ),
            ],
            options={
                "verbose_name": "법정동 최신 score",
                "verbose_name_plural": "법정동 최신 score",
                "db_table": "current_ldong",
            },
        ),
        migrations.CreateModel(
            name="CurrentAdong",
            fields=[
                (
                    "adong",
                    models.OneToOneField(
                        db_column="adong_code",
                        help_text="행정동 코드 (RDS current_adong.adong_code)",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="current_score",
                        serialize=False,
                        to="regions.adong",
                    ),
                ),
                (
                    "score_rent",
                    models.FloatField(
                        blank=True,
                        help_text="최근 1년 환산월세/㎡ 기반 score. 거래 0 동은 NULL",
                        null=True,
                    ),
                ),
                (
                    "score_amenity",
                    models.FloatField(help_text="생활/의료/공원 가중합 0~100"),
                ),
                (
                    "score_transit",
                    models.FloatField(
                        help_text=(
                            "지하철 1km anchor + 버스 면적당 밀도 p95 가중합 0~100"
                        )
                    ),
                ),
            ],
            options={
                "verbose_name": "행정동 최신 score",
                "verbose_name_plural": "행정동 최신 score",
                "db_table": "current_adong",
            },
        ),
        migrations.AddConstraint(
            model_name="currentseoul",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("score_amenity__gte", 0), ("score_amenity__lte", 100)
                ),
                name="ck_current_seoul_amenity",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentseoul",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("score_transit__gte", 0), ("score_transit__lte", 100)
                ),
                name="ck_current_seoul_transit",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentseoul",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("score_rent__gte", 0), ("score_rent__lte", 100)),
                    ("score_rent__isnull", True),
                    _connector="OR",
                ),
                name="ck_current_seoul_rent",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentgu",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("score_amenity__gte", 0), ("score_amenity__lte", 100)
                ),
                name="ck_current_gu_amenity",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentgu",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("score_transit__gte", 0), ("score_transit__lte", 100)
                ),
                name="ck_current_gu_transit",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentgu",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("score_rent__gte", 0), ("score_rent__lte", 100)),
                    ("score_rent__isnull", True),
                    _connector="OR",
                ),
                name="ck_current_gu_rent",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentldong",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("score_amenity__gte", 0), ("score_amenity__lte", 100)
                ),
                name="ck_current_ldong_amenity",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentldong",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("score_transit__gte", 0), ("score_transit__lte", 100)
                ),
                name="ck_current_ldong_transit",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentldong",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("score_rent__gte", 0), ("score_rent__lte", 100)),
                    ("score_rent__isnull", True),
                    _connector="OR",
                ),
                name="ck_current_ldong_rent",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentadong",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("score_amenity__gte", 0), ("score_amenity__lte", 100)
                ),
                name="ck_current_adong_amenity",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentadong",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("score_transit__gte", 0), ("score_transit__lte", 100)
                ),
                name="ck_current_adong_transit",
            ),
        ),
        migrations.AddConstraint(
            model_name="currentadong",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("score_rent__gte", 0), ("score_rent__lte", 100)),
                    ("score_rent__isnull", True),
                    _connector="OR",
                ),
                name="ck_current_adong_rent",
            ),
        ),
    ]
