"""sub-plan 4.5C — Park 모델을 schema.dbml line 268~275 정합.

변경 요약:
- PK: varchar(64) → varchar(50).
- name: NOT NULL (이미 OK).
- category: blank=True → NOT NULL.
- area_m2: NULL 허용 → NOT NULL.
- boundary: NULL 허용 → NOT NULL.
- location: NULL 허용 → NOT NULL.

데이터 호환:
- DP_DB park 1,886행 검증 결과: name/category/area_m2/boundary/location 전건 NOT NULL.
  → SLGI에 빈 테이블 상태로 적용되므로 NULL 제약 강화 안전 (단계 4.5E: SLGI volume drop).
"""

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parks", "0002_park_adong_fk"),
    ]

    operations = [
        # 1) PK varchar 길이: 64 → 50.
        migrations.AlterField(
            model_name="park",
            name="id",
            field=models.CharField(
                help_text=(
                    "공원 ID (RDS park.id, varchar(50)). "
                    "SHP UPIS_SHP_ZON216의 ID에서 끝 4자리 추출 후 P prefix. "
                    "예: 생활서비스시설_공원_0033 → P0033"
                ),
                max_length=50,
                primary_key=True,
                serialize=False,
            ),
        ),
        # 2) name: NOT NULL (help_text 정합만, 기존도 NOT NULL).
        migrations.AlterField(
            model_name="park",
            name="name",
            field=models.CharField(help_text="공원 이름 (NOT NULL)", max_length=200),
        ),
        # 3) category: blank=True → NOT NULL.
        migrations.AlterField(
            model_name="park",
            name="category",
            field=models.CharField(
                help_text=(
                    "공원 분류 (NOT NULL). 근린공원/어린이공원/도시자연공원/마을마당/광장 "
                    "등 SHP LABEL의 첫 분류 토큰"
                ),
                max_length=50,
            ),
        ),
        # 4) area_m2: NULL 허용 → NOT NULL.
        migrations.AlterField(
            model_name="park",
            name="area_m2",
            field=models.DecimalField(
                decimal_places=4,
                help_text="면적 (m^2, NOT NULL)",
                max_digits=20,
            ),
        ),
        # 5) boundary: NULL 허용 → NOT NULL.
        migrations.AlterField(
            model_name="park",
            name="boundary",
            field=django.contrib.gis.db.models.fields.MultiPolygonField(
                help_text="공원 경계 (WGS84, NOT NULL)",
                srid=4326,
            ),
        ),
        # 6) location: NULL 허용 → NOT NULL.
        migrations.AlterField(
            model_name="park",
            name="location",
            field=django.contrib.gis.db.models.fields.PointField(
                help_text="중심점 (WGS84, NOT NULL)",
                srid=4326,
            ),
        ),
    ]
