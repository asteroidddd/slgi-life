"""sub-plan 7G-C (결정 5A) — Dong 모델 + dong 테이블 폐기.

Dong (db_table='dong')은 regions.Adong + 합성 score 컬럼으로 완전 대체된다.
neighborhoods 앱 자체는 view·serializer만 가진 빈 앱으로 유지.

작업 순서 lock (사용자 brief 7G-C 명시):
1. users.0003_favorite_dong_to_adong  → Favorite.dong FK 제거 + Favorite.adong FK 추가
2. subway.0006_delete_nearest_subway  → NearestSubway 모델·테이블 제거 (Dong FK 해제)
3. neighborhoods.0003_delete_dong (본 파일) → Dong 모델 + dong 테이블 DROP

users.0003 / subway.0006 이 미적용 상태에서 본 마이그레이션이 적용되면
Dong CASCADE 의존성이 남아 DROP에 실패할 수 있다. dependencies에 명시한다.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("neighborhoods", "0002_alter_dong_code"),
        # All legacy neighborhoods.Dong references must be removed before
        # the Dong model/table is dropped during a fresh migration.
        ("amenities", "0005_amenity_v2"),
        ("bus", "0003_step4_5B_schema_align"),
        ("parks", "0002_park_adong_fk"),
        ("populations", "0002_adong_population_fk"),
        ("regions", "0005_adong_adjacency_fk"),
        ("rent_deal", "0003_step4_5B_schema_align"),
        ("store", "0003_step4_5B_schema_align"),
        # Favorite.dong FK 제거 선행. 결정 F1-A.
        ("users", "0003_favorite_dong_to_adong"),
        # NearestSubway.dong FK 제거 선행. 결정 4A.
        ("subway", "0006_delete_nearest_subway"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Dong",
        ),
    ]
