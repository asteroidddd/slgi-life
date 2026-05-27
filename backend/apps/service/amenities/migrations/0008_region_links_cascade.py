"""Cascade amenity-region relation rows when regions are removed."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0007_rename_adjacent_ad_adong_c_c2bcba_idx_adjacent_ad_adong1__7a7873_idx_and_more"),
        ("amenities", "0007_remove_amenity_amenity_dong_id_7a8d1d_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="amenityadong",
            name="adong",
            field=models.ForeignKey(
                db_column="adong_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="amenity_links",
                to="regions.adong",
            ),
        ),
        migrations.AlterField(
            model_name="amenityldong",
            name="ldong",
            field=models.ForeignKey(
                db_column="ldong_code",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="amenity_links",
                to="regions.ldong",
            ),
        ),
    ]
