"""sub-plan 4.5A — regions 앱 모델을 DP_DB schema.dbml과 1:1 정합화.

변경 요약 (DB 0행 가정. 컬럼 다운사이즈 포함):
- Seoul.code           : varchar(10) → varchar(20)
- Seoul.name           : varchar(50) → varchar(100)
- Gu.gu_code           : varchar(10) → varchar(20)
- Gu.name              : varchar(50) → varchar(100)
- Gu.slug              : 신규 (varchar(80) unique, null 허용 — ETL 적재 후 NOT NULL은 4.5B 이후)
- Ldong.ldong_code     : varchar(10) → varchar(20)
- Ldong.name           : varchar(50) → varchar(100)
- Ldong.slug           : 신규 (varchar(80) unique, null 허용)
- GuAdjacency          : db_column gu_code_a/_b → gu1_code/gu2_code
- LdongAdjacency       : db_column ldong_code_a/_b → ldong1_code/ldong2_code
- AdongAdjacency       : db_column adong_code_a/_b → adong1_code/adong2_code

slug NOT NULL 강제 및 인접 a == b 방지 CHECK 제약은 4.5B/C ETL 단계에서 처리.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0005_adong_adjacency_fk"),
    ]

    operations = [
        # 1) Seoul - code/name length
        migrations.AlterField(
            model_name="seoul",
            name="code",
            field=models.CharField(
                help_text="서울시 코드 (RDS seoul.code)",
                max_length=20,
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name="seoul",
            name="name",
            field=models.CharField(help_text="이름 (예: '서울특별시')", max_length=100),
        ),
        # 2) Gu - gu_code/name length + slug 추가
        migrations.AlterField(
            model_name="gu",
            name="gu_code",
            field=models.CharField(
                help_text="자치구 코드 (RDS gu.gu_code)",
                max_length=20,
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name="gu",
            name="name",
            field=models.CharField(help_text="구 이름 (예: '중구')", max_length=100),
        ),
        migrations.AddField(
            model_name="gu",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="URL용 고유 식별자. gu.name과 동일값 (예: 강남구)",
                max_length=80,
                null=True,
                unique=True,
            ),
        ),
        # 3) Ldong - ldong_code/name length + slug 추가
        migrations.AlterField(
            model_name="ldong",
            name="ldong_code",
            field=models.CharField(
                help_text="법정동 코드 (RDS ldong.ldong_code)",
                max_length=20,
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name="ldong",
            name="name",
            field=models.CharField(help_text="법정동 이름", max_length=100),
        ),
        migrations.AddField(
            model_name="ldong",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="URL용 고유 식별자. 패턴: <gu_name>-<name> (예: 강남구-신사동)",
                max_length=80,
                null=True,
                unique=True,
            ),
        ),
        # 4) GuAdjacency - db_column rename
        migrations.AlterField(
            model_name="guadjacency",
            name="gu_a",
            field=models.ForeignKey(
                db_column="gu1_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="adjacency_a",
                to="regions.gu",
            ),
        ),
        migrations.AlterField(
            model_name="guadjacency",
            name="gu_b",
            field=models.ForeignKey(
                db_column="gu2_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="adjacency_b",
                to="regions.gu",
            ),
        ),
        # 5) LdongAdjacency - db_column rename
        migrations.AlterField(
            model_name="ldongadjacency",
            name="ldong_a",
            field=models.ForeignKey(
                db_column="ldong1_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="adjacency_a",
                to="regions.ldong",
            ),
        ),
        migrations.AlterField(
            model_name="ldongadjacency",
            name="ldong_b",
            field=models.ForeignKey(
                db_column="ldong2_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="adjacency_b",
                to="regions.ldong",
            ),
        ),
        # 6) AdongAdjacency - db_column rename
        migrations.AlterField(
            model_name="adongadjacency",
            name="adong_a",
            field=models.ForeignKey(
                db_column="adong1_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="adjacency_a",
                to="regions.adong",
            ),
        ),
        migrations.AlterField(
            model_name="adongadjacency",
            name="adong_b",
            field=models.ForeignKey(
                db_column="adong2_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="adjacency_b",
                to="regions.adong",
            ),
        ),
    ]
