"""Allow libraries to survive region remapping."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0007_rename_adjacent_ad_adong_c_c2bcba_idx_adjacent_ad_adong1__7a7873_idx_and_more"),
        ("library", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="library",
            name="adong",
            field=models.ForeignKey(
                blank=True,
                db_column="adong_code",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="libraries",
                to="regions.adong",
            ),
        ),
        migrations.AlterField(
            model_name="library",
            name="ldong",
            field=models.ForeignKey(
                blank=True,
                db_column="ldong_code",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="libraries",
                to="regions.ldong",
            ),
        ),
    ]
