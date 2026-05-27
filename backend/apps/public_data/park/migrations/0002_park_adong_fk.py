"""sub-plan 2O — ParkDong FK dong -> adong (regions.Adong).

DB 변경 0: db_column은 `adong_code` 동일 유지. FK target만
neighborhoods.Dong(to_field='code') -> regions.Adong(PK=adong_code)로 치환.

RenameField + AlterField + unique_together/index 재선언 패턴.

NOTE: park app_label = "parks" (apps.py 참조). model_name은 소문자 'parkdong'.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parks", "0001_initial"),
        ("regions", "0004_add_adong"),
    ]

    operations = [
        # 1) field rename: dong -> adong (state+db).
        migrations.RenameField(
            model_name="parkdong",
            old_name="dong",
            new_name="adong",
        ),
        # 2) FK target 치환: neighborhoods.Dong(to_field='code') -> regions.Adong.
        migrations.AlterField(
            model_name="parkdong",
            name="adong",
            field=models.ForeignKey(
                db_column="adong_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="park_dongs",
                to="regions.adong",
            ),
        ),
        # 3) unique_together / index 재선언 — field name 변경 반영.
        migrations.AlterUniqueTogether(
            name="parkdong",
            unique_together={("park", "adong")},
        ),
        migrations.RemoveIndex(
            model_name="parkdong",
            name="park_adong_adong_c_30d82b_idx",
        ),
        migrations.AddIndex(
            model_name="parkdong",
            index=models.Index(fields=["adong"], name="park_adong_adong_c_30d82b_idx"),
        ),
    ]
