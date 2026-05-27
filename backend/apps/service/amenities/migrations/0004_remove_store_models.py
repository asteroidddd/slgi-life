"""Sub-plan 2E — Store + BusinessCategory + KsciCategory state+database DeleteModel.

해결책 B (2D와 동일 패턴): 기존 0001~0003은 유지. 별도 0004에서 3 모델 모두
state + database DeleteModel. `store/0001_initial`에서 동일 3 모델을
state+database CreateModel로 재생성한다. fresh migrate 시
0001 (생성) → 0002 (3 모델 생성) → 0003 (alter) → 0004 (drop) → store/0001 (재생성).
단계 5 docker fresh migrate 환경에서 SLGI DB는 데이터 0행이므로 drop→recreate
비용은 무해.

Amenity 모델은 본 sub-plan에서 변경 없음 — sub-plan 2J에서 처리 예정.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("amenities", "0003_rename_store_subcate_3bbcf7_idx_store_categor_a63bc0_idx_and_more"),
    ]

    operations = [
        # default DeleteModel = state + database 모두 drop.
        # Store가 BusinessCategory / KsciCategory를 FK 참조하므로 Store 먼저.
        migrations.DeleteModel(name="Store"),
        migrations.DeleteModel(name="BusinessCategory"),
        migrations.DeleteModel(name="KsciCategory"),
    ]
