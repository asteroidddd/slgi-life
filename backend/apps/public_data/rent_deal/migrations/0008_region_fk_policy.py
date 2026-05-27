"""Relax rent-deal region FKs for region snapshot replacement."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0007_rename_adjacent_ad_adong_c_c2bcba_idx_adjacent_ad_adong1__7a7873_idx_and_more"),
        ("rent_deal", "0007_rent_deal_ldong_adong_map"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rentdeal",
            name="adong",
            field=models.ForeignKey(
                blank=True,
                db_column="adong_code",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="rent_deals",
                to="regions.adong",
            ),
        ),
        migrations.AlterField(
            model_name="rentdeal",
            name="ldong",
            field=models.ForeignKey(
                blank=True,
                db_column="ldong_code",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="rent_deals",
                to="regions.ldong",
            ),
        ),
        migrations.AlterField(
            model_name="rentdealldongadongmap",
            name="adong",
            field=models.ForeignKey(
                blank=True,
                db_column="adong_code",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="rent_deal_ldong_maps",
                to="regions.adong",
            ),
        ),
        migrations.AlterField(
            model_name="rentdealldongadongmap",
            name="ldong",
            field=models.OneToOneField(
                db_column="ldong_code",
                on_delete=django.db.models.deletion.CASCADE,
                primary_key=True,
                related_name="rent_deal_adong_map",
                serialize=False,
                to="regions.ldong",
            ),
        ),
    ]
