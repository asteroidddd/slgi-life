"""sub-plan 2O — AdongPopulation FK dong -> adong (regions.Adong).

DB 변경 0: db_column은 `adong_code` 동일 유지. FK target만
neighborhoods.Dong(to_field='code') -> regions.Adong(PK=adong_code)로 치환.

RenameField + AlterField + unique_together/index 재선언 패턴.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("populations", "0001_initial"),
        ("regions", "0004_add_adong"),
    ]

    operations = [
        # 1) field rename: dong -> adong (state+db).
        migrations.RenameField(
            model_name="adongpopulation",
            old_name="dong",
            new_name="adong",
        ),
        # 2) FK target 치환: neighborhoods.Dong(to_field='code') -> regions.Adong.
        migrations.AlterField(
            model_name="adongpopulation",
            name="adong",
            field=models.ForeignKey(
                db_column="adong_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="populations",
                to="regions.adong",
            ),
        ),
        # 3) unique_together / index 재선언 — field name 변경 반영.
        migrations.AlterUniqueTogether(
            name="adongpopulation",
            unique_together={("adong", "date")},
        ),
        migrations.RemoveIndex(
            model_name="adongpopulation",
            name="adong_popul_adong_c_d66610_idx",
        ),
        migrations.AddIndex(
            model_name="adongpopulation",
            index=models.Index(
                fields=["adong", "-date"], name="adong_popul_adong_c_d66610_idx"
            ),
        ),
    ]
