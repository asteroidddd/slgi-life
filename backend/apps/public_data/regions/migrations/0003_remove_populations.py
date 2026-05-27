"""sub-plan 2C — regions app에서 LdongPopulation / AdongPopulation을 ORM 상으로만 제거.

`SeparateDatabaseAndState`를 사용하여 실제 DB 변경은 발생시키지 않는다. 두 모델은
`apps.public_data.populations`의 `0001_initial`에서 동일한 db_table로 재선언된다.

이 migration과 `populations.0001_initial`은 한 쌍으로 동시에 적용되어야 한다.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0002_rename_ldong_gu_id_9eac56_idx_ldong_gu_code_af3dfe_idx_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="LdongPopulation"),
                migrations.DeleteModel(name="AdongPopulation"),
            ],
            database_operations=[],
        ),
    ]
