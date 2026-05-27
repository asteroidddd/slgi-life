"""sub-plan 2C — LdongPopulation / AdongPopulation을 populations app으로 옮기는 state-only 마이그레이션.

`SeparateDatabaseAndState`로 ORM 인식만 이쪽 app에 등록하고, 실제 DB 객체는
기존 `regions.0001_initial`이 만들어 둔 테이블·인덱스·제약을 그대로 사용한다.
DB 변경은 발생하지 않는다.

이 migration은 `regions.0003_remove_populations`와 한 쌍으로 동시에 적용되어야 한다.
state_operations의 필드 정의는 `regions.0001_initial`의 LdongPopulation /
AdongPopulation CreateModel 블록과 1:1로 동일하게 맞춘다 (index 이름 포함).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("regions", "0003_remove_populations"),
        ("neighborhoods", "0002_alter_dong_code"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="LdongPopulation",
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
                        ("date", models.DateField(help_text="기준일")),
                        (
                            "total_population",
                            models.IntegerField(blank=True, help_text="총 인구", null=True),
                        ),
                        (
                            "household_count",
                            models.IntegerField(blank=True, help_text="세대 수", null=True),
                        ),
                        (
                            "male_population",
                            models.IntegerField(blank=True, help_text="남자 인구", null=True),
                        ),
                        (
                            "female_population",
                            models.IntegerField(blank=True, help_text="여자 인구", null=True),
                        ),
                        (
                            "ldong",
                            models.ForeignKey(
                                db_column="ldong_code",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="populations",
                                to="regions.ldong",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "법정동 인구",
                        "verbose_name_plural": "법정동 인구",
                        "db_table": "ldong_population",
                        "ordering": ["-date"],
                        "indexes": [
                            models.Index(
                                fields=["ldong", "-date"],
                                name="ldong_popul_ldong_c_9123bf_idx",
                            ),
                            models.Index(fields=["date"], name="ldong_popul_date_4249ae_idx"),
                        ],
                        "unique_together": {("ldong", "date")},
                    },
                ),
                migrations.CreateModel(
                    name="AdongPopulation",
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
                        ("date", models.DateField(help_text="기준일")),
                        (
                            "total_population",
                            models.IntegerField(blank=True, help_text="총 인구", null=True),
                        ),
                        (
                            "household_count",
                            models.IntegerField(blank=True, help_text="세대 수", null=True),
                        ),
                        (
                            "male_population",
                            models.IntegerField(blank=True, help_text="남자 인구", null=True),
                        ),
                        (
                            "female_population",
                            models.IntegerField(blank=True, help_text="여자 인구", null=True),
                        ),
                        (
                            "dong",
                            models.ForeignKey(
                                db_column="adong_code",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="populations",
                                to="neighborhoods.dong",
                                to_field="code",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "행정동 인구",
                        "verbose_name_plural": "행정동 인구",
                        "db_table": "adong_population",
                        "ordering": ["-date"],
                        "indexes": [
                            models.Index(
                                fields=["dong", "-date"],
                                name="adong_popul_adong_c_d66610_idx",
                            ),
                            models.Index(fields=["date"], name="adong_popul_date_2c797b_idx"),
                        ],
                        "unique_together": {("dong", "date")},
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
