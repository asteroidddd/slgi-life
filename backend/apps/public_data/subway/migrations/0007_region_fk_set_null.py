"""Allow subway stations to survive region remapping."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0007_rename_adjacent_ad_adong_c_c2bcba_idx_adjacent_ad_adong1__7a7873_idx_and_more"),
        ("subway", "0006_delete_nearest_subway"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subwaystation",
            name="adong",
            field=models.ForeignKey(
                blank=True,
                db_column="adong_code",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="subway_stations",
                to="regions.adong",
            ),
        ),
        migrations.AlterField(
            model_name="subwaystation",
            name="ldong",
            field=models.ForeignKey(
                blank=True,
                db_column="ldong_code",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="subway_stations",
                to="regions.ldong",
            ),
        ),
    ]
