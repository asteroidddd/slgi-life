"""sub-plan 7G-C (결정 4A) — legacy NearestSubway 모델 + nearest_subway 테이블 폐기.

NearestSubway는 neighborhoods.Dong FK 기반 legacy 캐시 (sub-plan 4.5B lock D 보존).
7G-C에서 Dong 모델 자체가 제거되므로, 그 전제로 NearestSubway 모델도 제거한다.
NearestSubwayAdong/NearestSubwayLdong (regions.Adong/Ldong FK)이 완전 대체.

DROP TABLE nearest_subway는 본 마이그레이션이 자동 수행한다.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("subway", "0005_rename_subway_stat_adong_idx_subway_stat_adong_c_77e870_idx_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="NearestSubway",
        ),
    ]
