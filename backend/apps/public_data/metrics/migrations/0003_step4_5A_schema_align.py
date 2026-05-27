"""sub-plan 4.5A — metrics 앱 모델을 DP_DB schema.dbml과 1:1 정합화.

변경 요약 (DB 0행 가정):
- Metric.metric_code             : varchar(30) → varchar(50)
- Metric.name / unit / category  : Char NOT NULL (blank=False)
- Metric.source_item             : varchar(200) → varchar(100)
- Metric.source_classification_code : varchar(100) → varchar(50)
- Metric.cycle / source_agency / source_table / generation_method / remarks :
  NULL 허용 명시 (Char/Text + null=True)
- GuMetric.value                 : NULL 허용 제거 → NOT NULL
- SeoulMetric.value              : NULL 허용 제거 → NOT NULL
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("metrics", "0002_extend_metric_code_length"),
    ]

    operations = [
        # Metric.metric_code length
        migrations.AlterField(
            model_name="metric",
            name="metric_code",
            field=models.CharField(
                help_text="지표 코드 (RDS metric.metric_code)",
                max_length=50,
                primary_key=True,
                serialize=False,
            ),
        ),
        # Metric NOT NULL (name/unit/category — Char blank=False)
        migrations.AlterField(
            model_name="metric",
            name="unit",
            field=models.CharField(help_text="단위 (예: '명', '%', '원')", max_length=30),
        ),
        migrations.AlterField(
            model_name="metric",
            name="category",
            field=models.CharField(help_text="카테고리", max_length=50),
        ),
        # Metric NULL 허용 명시
        migrations.AlterField(
            model_name="metric",
            name="cycle",
            field=models.CharField(
                blank=True, help_text="갱신 주기 (A/M/D)", max_length=20, null=True
            ),
        ),
        migrations.AlterField(
            model_name="metric",
            name="generation_method",
            field=models.TextField(blank=True, help_text="생성 방법 설명", null=True),
        ),
        migrations.AlterField(
            model_name="metric",
            name="source_agency",
            field=models.CharField(
                blank=True, help_text="출처 기관", max_length=100, null=True
            ),
        ),
        migrations.AlterField(
            model_name="metric",
            name="source_table",
            field=models.CharField(
                blank=True, help_text="출처 테이블/통계표", max_length=100, null=True
            ),
        ),
        # Metric.source_item varchar(200→100) + NULL 허용
        migrations.AlterField(
            model_name="metric",
            name="source_item",
            field=models.CharField(
                blank=True, help_text="출처 항목명", max_length=100, null=True
            ),
        ),
        # Metric.source_classification_code varchar(100→50) + NULL 허용
        migrations.AlterField(
            model_name="metric",
            name="source_classification_code",
            field=models.CharField(
                blank=True, help_text="출처 분류 코드", max_length=50, null=True
            ),
        ),
        migrations.AlterField(
            model_name="metric",
            name="remarks",
            field=models.TextField(blank=True, help_text="비고", null=True),
        ),
        # GuMetric.value NOT NULL
        migrations.AlterField(
            model_name="gumetric",
            name="value",
            field=models.DecimalField(
                decimal_places=6, help_text="지표 값", max_digits=20
            ),
        ),
        # SeoulMetric.value NOT NULL
        migrations.AlterField(
            model_name="seoulmetric",
            name="value",
            field=models.DecimalField(
                decimal_places=6, help_text="지표 값", max_digits=20
            ),
        ),
    ]
