"""sub-plan 4.5A — LdongPopulation / AdongPopulation 인구 4개 컬럼을 NOT NULL 화.

DP_DB schema.dbml 정합:
- total_population / household_count / male_population / female_population : NOT NULL

DB 0행 가정 (RDS 적재 전). 데이터 적재 후 NOT NULL 제약 위반 방지는 ETL 단계에서
DataFrame validation으로 보장.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("populations", "0002_adong_population_fk"),
    ]

    operations = [
        # LdongPopulation
        migrations.AlterField(
            model_name="ldongpopulation",
            name="total_population",
            field=models.IntegerField(help_text="총 인구"),
        ),
        migrations.AlterField(
            model_name="ldongpopulation",
            name="household_count",
            field=models.IntegerField(help_text="세대 수"),
        ),
        migrations.AlterField(
            model_name="ldongpopulation",
            name="male_population",
            field=models.IntegerField(help_text="남자 인구"),
        ),
        migrations.AlterField(
            model_name="ldongpopulation",
            name="female_population",
            field=models.IntegerField(help_text="여자 인구"),
        ),
        # AdongPopulation
        migrations.AlterField(
            model_name="adongpopulation",
            name="total_population",
            field=models.IntegerField(help_text="총 인구"),
        ),
        migrations.AlterField(
            model_name="adongpopulation",
            name="household_count",
            field=models.IntegerField(help_text="세대 수"),
        ),
        migrations.AlterField(
            model_name="adongpopulation",
            name="male_population",
            field=models.IntegerField(help_text="남자 인구"),
        ),
        migrations.AlterField(
            model_name="adongpopulation",
            name="female_population",
            field=models.IntegerField(help_text="여자 인구"),
        ),
    ]
