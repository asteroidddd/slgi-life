# Generated for rent_deal ldong-adong single map on 2026-05-20.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0007_rename_adjacent_ad_adong_c_c2bcba_idx_adjacent_ad_adong1__7a7873_idx_and_more"),
        ("rent_deal", "0006_rentdeal_adong"),
    ]

    operations = [
        migrations.CreateModel(
            name="RentDealLdongAdongMap",
            fields=[
                (
                    "ldong",
                    models.OneToOneField(
                        db_column="ldong_code",
                        help_text="Legal dong. One mapping decision per ldong.",
                        on_delete=django.db.models.deletion.PROTECT,
                        primary_key=True,
                        related_name="rent_deal_adong_map",
                        serialize=False,
                        to="regions.ldong",
                    ),
                ),
                (
                    "adong",
                    models.ForeignKey(
                        blank=True,
                        db_column="adong_code",
                        help_text="Admin dong when this ldong maps to exactly one adong; otherwise NULL.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rent_deal_ldong_maps",
                        to="regions.adong",
                    ),
                ),
            ],
            options={
                "verbose_name": "rent deal ldong-adong map",
                "verbose_name_plural": "rent deal ldong-adong maps",
                "db_table": "rent_deal_ldong_adong_map",
            },
        ),
        migrations.AddIndex(
            model_name="rentdealldongadongmap",
            index=models.Index(fields=["adong"], name="rent_ld_ad_map_adong_idx"),
        ),
    ]
