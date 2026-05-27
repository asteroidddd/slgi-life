"""sub-plan 4.5C — Amenity created_at / updated_at 컬럼 제거.

schema.dbml line 365~376 정본에 created_at/updated_at 컬럼이 없다.
RDS 이전 시 컬럼 불일치를 방지하기 위해 SLGI에서도 제거한다.

데이터 호환:
- SLGI volume drop 후 fresh migrate (단계 4.5E)이므로 데이터 손실 없음.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("amenities", "0005_amenity_v2"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="amenity",
            name="created_at",
        ),
        migrations.RemoveField(
            model_name="amenity",
            name="updated_at",
        ),
    ]
