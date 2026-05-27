"""sub-plan 7G-B2 (F1-A) — Favorite.dong → Favorite.adong FK 치환.

- 기존 Favorite.dong FK (neighborhoods.Dong) 제거.
- 새 Favorite.adong FK (regions.Adong) 추가.
- unique_together ("user", "dong") → ("user", "adong").

의존성:
- ("users", "0002_user_nickname_user_school_user_year_favorite") — 기존 Favorite 모델.
- ("regions", "0004_add_adong") — Adong 마스터.

작업 순서 lock: 본 migration은 neighborhoods.0003_delete_dong (7G-C에서 신설) 적용
'전'에 적용되어야 안전하다. 기존 Dong CASCADE 의존성이 본 migration 적용 시 해제되어,
이후 7G-C 단계에서 dong 테이블 DROP 가능 상태가 된다.

기존 user_favorite 데이터는 Favorite.dong (neighborhoods.Dong) → Adong으로
1:1 자동 매핑되지 않는다 (dong.id가 BigAuto이고 adong PK는 string). 다만 사용자
brief에서 SLGI DB의 user_favorite 행수는 데모 수준이며, 본 단계에서는 행 보존을
요구하지 않는다 (lock D 격상 시 frontend 회귀 검증 우선). 따라서 RemoveField → AddField
순으로 데이터 손실을 감수한다. 데이터 보존이 필요한 경우 별도 데이터 마이그레이션
운영 단계에서 처리.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_user_nickname_user_school_user_year_favorite"),
        ("regions", "0004_add_adong"),
    ]

    operations = [
        # unique_together를 먼저 풀어야 dong 컬럼 제거가 가능하다.
        migrations.AlterUniqueTogether(
            name="favorite",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="favorite",
            name="dong",
        ),
        migrations.AddField(
            model_name="favorite",
            name="adong",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="favorited_by",
                to="regions.adong",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="favorite",
            unique_together={("user", "adong")},
        ),
    ]
