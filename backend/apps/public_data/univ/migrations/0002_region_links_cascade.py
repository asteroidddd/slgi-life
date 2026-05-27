"""Cascade university-region relation rows when regions are removed."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0007_rename_adjacent_ad_adong_c_c2bcba_idx_adjacent_ad_adong1__7a7873_idx_and_more"),
        ("univ", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="univadong",
            name="adong",
            field=models.ForeignKey(
                db_column="adong_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="univ_links",
                to="regions.adong",
            ),
        ),
        migrations.AlterField(
            model_name="univldong",
            name="ldong",
            field=models.ForeignKey(
                db_column="ldong_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="univ_links",
                to="regions.ldong",
            ),
        ),
    ]
