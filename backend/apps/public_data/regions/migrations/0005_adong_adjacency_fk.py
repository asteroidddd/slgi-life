"""sub-plan 2O — AdongAdjacency FK dong_a/dong_b -> adong_a/adong_b (regions.Adong).

DB 변경 0: db_column은 `adong_code_a`/`adong_code_b` 동일 유지. FK target만
neighborhoods.Dong(to_field='code') -> regions.Adong(PK=adong_code)로 치환.

RenameField + AlterField + unique_together/index 재선언 패턴.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0004_add_adong"),
        ("neighborhoods", "0002_alter_dong_code"),
    ]

    operations = [
        # 1) field rename: dong_a -> adong_a, dong_b -> adong_b (state+db).
        migrations.RenameField(
            model_name="adongadjacency",
            old_name="dong_a",
            new_name="adong_a",
        ),
        migrations.RenameField(
            model_name="adongadjacency",
            old_name="dong_b",
            new_name="adong_b",
        ),
        # 2) FK target 치환: neighborhoods.Dong(to_field='code') -> regions.Adong.
        #    db_column 유지(adong_code_a/_b) → 실제 DB column은 변화 없음.
        migrations.AlterField(
            model_name="adongadjacency",
            name="adong_a",
            field=models.ForeignKey(
                db_column="adong_code_a",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="adjacency_a",
                to="regions.adong",
            ),
        ),
        migrations.AlterField(
            model_name="adongadjacency",
            name="adong_b",
            field=models.ForeignKey(
                db_column="adong_code_b",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="adjacency_b",
                to="regions.adong",
            ),
        ),
        # 3) unique_together / index 재선언 — field name 변경 반영.
        migrations.AlterUniqueTogether(
            name="adongadjacency",
            unique_together={("adong_a", "adong_b")},
        ),
        migrations.RemoveIndex(
            model_name="adongadjacency",
            name="adjacent_ad_adong_c_c2bcba_idx",
        ),
        migrations.RemoveIndex(
            model_name="adongadjacency",
            name="adjacent_ad_adong_c_0eabdf_idx",
        ),
        migrations.AddIndex(
            model_name="adongadjacency",
            index=models.Index(fields=["adong_a"], name="adjacent_ad_adong_c_c2bcba_idx"),
        ),
        migrations.AddIndex(
            model_name="adongadjacency",
            index=models.Index(fields=["adong_b"], name="adjacent_ad_adong_c_0eabdf_idx"),
        ),
    ]
