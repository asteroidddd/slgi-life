# Generated manually for operational cache tables.

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RegionParkAreaCache",
            fields=[
                ("cache_key", models.CharField(max_length=40, primary_key=True, serialize=False)),
                ("region_type", models.CharField(max_length=10)),
                ("region_code", models.CharField(max_length=20)),
                ("park_count", models.PositiveIntegerField(default=0)),
                ("park_area_m2", models.FloatField(default=0)),
                ("region_area_m2", models.FloatField(blank=True, null=True)),
                ("park_area_ratio", models.FloatField(default=0)),
                ("source_version", models.CharField(max_length=40)),
                ("computed_at", models.DateTimeField()),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
            ],
            options={
                "db_table": "region_park_area_cache",
                "verbose_name": "region park area cache",
                "verbose_name_plural": "region park area caches",
            },
        ),
        migrations.CreateModel(
            name="RegionAmenityCategoryCache",
            fields=[
                ("cache_key", models.CharField(max_length=80, primary_key=True, serialize=False)),
                ("region_type", models.CharField(max_length=10)),
                ("region_code", models.CharField(max_length=20)),
                ("category", models.CharField(max_length=30)),
                ("amenity_count", models.PositiveIntegerField(default=0)),
                ("density_per_km2", models.FloatField(blank=True, null=True)),
                ("region_area_m2", models.FloatField(blank=True, null=True)),
                ("source_version", models.CharField(max_length=40)),
                ("computed_at", models.DateTimeField()),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
            ],
            options={
                "db_table": "region_amenity_category_cache",
                "verbose_name": "region amenity category cache",
                "verbose_name_plural": "region amenity category caches",
            },
        ),
        migrations.AddConstraint(
            model_name="regionparkareacache",
            constraint=models.UniqueConstraint(
                fields=("region_type", "region_code"),
                name="uq_region_park_area_cache_region",
            ),
        ),
        migrations.AddIndex(
            model_name="regionparkareacache",
            index=models.Index(fields=["region_type"], name="region_park_type_idx"),
        ),
        migrations.AddIndex(
            model_name="regionparkareacache",
            index=models.Index(fields=["source_version"], name="region_park_source_idx"),
        ),
        migrations.AddConstraint(
            model_name="regionamenitycategorycache",
            constraint=models.UniqueConstraint(
                fields=("region_type", "region_code", "category"),
                name="uq_region_amenity_cache_region_category",
            ),
        ),
        migrations.AddIndex(
            model_name="regionamenitycategorycache",
            index=models.Index(fields=["region_type", "category"], name="region_amenity_type_cat_idx"),
        ),
        migrations.AddIndex(
            model_name="regionamenitycategorycache",
            index=models.Index(fields=["region_code"], name="region_amenity_code_idx"),
        ),
        migrations.AddIndex(
            model_name="regionamenitycategorycache",
            index=models.Index(fields=["source_version"], name="region_amenity_source_idx"),
        ),
    ]
