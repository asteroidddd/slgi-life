# Generated manually for rent_deal_service.

import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RentDealCache",
            fields=[
                (
                    "id",
                    models.CharField(
                        max_length=60,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("housing_type", models.CharField(max_length=10)),
                (
                    "deposit",
                    models.IntegerField(help_text="Deposit amount in KRW 10,000 units."),
                ),
                (
                    "monthly_rent",
                    models.IntegerField(help_text="Monthly rent in KRW 10,000 units."),
                ),
                (
                    "converted_rent",
                    models.FloatField(
                        help_text=(
                            "Monthly rent plus deposit conversion, in KRW 10,000 units."
                        )
                    ),
                ),
                ("area_m2", models.FloatField(blank=True, null=True)),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True,
                        geography=False,
                        null=True,
                        srid=4326,
                    ),
                ),
            ],
            options={
                "db_table": "rent_deal_cache",
                "verbose_name": "rent deal cache",
                "verbose_name_plural": "rent deal caches",
                "indexes": [
                    models.Index(
                        fields=["housing_type"],
                        name="rent_cache_type_idx",
                    ),
                    models.Index(
                        fields=["converted_rent"],
                        name="rent_cache_conv_idx",
                    ),
                    models.Index(
                        fields=["area_m2"],
                        name="rent_cache_area_idx",
                    ),
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["location"],
                        name="rent_cache_loc_gist_idx",
                    ),
                ],
            },
        ),
    ]
