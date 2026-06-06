# Generated manually for map display cache tables.

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="MapAmenityMarkerCache",
            fields=[
                ("id", models.BigIntegerField(primary_key=True, serialize=False)),
                ("category", models.CharField(max_length=30)),
                ("name", models.CharField(max_length=200)),
                ("location", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "map_amenity_marker_cache",
                "verbose_name": "map amenity marker cache",
                "verbose_name_plural": "map amenity marker caches",
                "indexes": [
                    models.Index(fields=["category", "name"], name="map_amenity_cat_name_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="MapMedicalMarkerCache",
            fields=[
                ("hpid", models.CharField(max_length=20, primary_key=True, serialize=False)),
                ("category", models.CharField(max_length=20)),
                ("type", models.CharField(max_length=30)),
                ("name", models.CharField(max_length=200)),
                ("address", models.CharField(blank=True, default="", max_length=255)),
                ("tel1", models.CharField(blank=True, default="", max_length=50)),
                ("location", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("is_emergency", models.BooleanField(default=False)),
                ("hours_summary", models.JSONField(default=dict)),
                ("specialty_groups", models.JSONField(default=list)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "map_medical_marker_cache",
                "verbose_name": "map medical marker cache",
                "verbose_name_plural": "map medical marker caches",
                "indexes": [
                    models.Index(fields=["category", "name"], name="map_medical_cat_name_idx"),
                    models.Index(fields=["is_emergency"], name="map_medical_emergency_idx"),
                ],
            },
        ),
    ]
