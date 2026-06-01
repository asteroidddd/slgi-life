# Generated manually for operational cache tables.

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RentDealGeocodeCache",
            fields=[
                ("cache_key", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("normalized_query", models.CharField(max_length=255, unique=True)),
                ("gu_code", models.CharField(blank=True, max_length=20, null=True)),
                ("ldong_code", models.CharField(blank=True, max_length=20, null=True)),
                ("jibun", models.CharField(blank=True, max_length=50, null=True)),
                ("provider", models.CharField(default="imported", max_length=30)),
                ("status", models.CharField(max_length=20)),
                ("lng", models.FloatField(blank=True, null=True)),
                ("lat", models.FloatField(blank=True, null=True)),
                ("adong_code", models.CharField(blank=True, max_length=20, null=True)),
                ("error", models.CharField(blank=True, max_length=255, null=True)),
                ("hit_count", models.PositiveIntegerField(default=0)),
                ("first_seen_at", models.DateTimeField()),
                ("last_used_at", models.DateTimeField()),
                ("fetched_at", models.DateTimeField(blank=True, null=True)),
                ("raw_response", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
            ],
            options={
                "db_table": "rent_deal_geocode_cache",
                "verbose_name": "rent deal geocode cache",
                "verbose_name_plural": "rent deal geocode caches",
            },
        ),
        migrations.AddIndex(
            model_name="rentdealgeocodecache",
            index=models.Index(fields=["ldong_code", "jibun"], name="rent_geo_ldong_jibun_idx"),
        ),
        migrations.AddIndex(
            model_name="rentdealgeocodecache",
            index=models.Index(fields=["status"], name="rent_geo_status_idx"),
        ),
        migrations.AddIndex(
            model_name="rentdealgeocodecache",
            index=models.Index(fields=["provider"], name="rent_geo_provider_idx"),
        ),
        migrations.AddIndex(
            model_name="rentdealgeocodecache",
            index=models.Index(fields=["adong_code"], name="rent_geo_adong_idx"),
        ),
        migrations.AddIndex(
            model_name="rentdealgeocodecache",
            index=models.Index(fields=["last_used_at"], name="rent_geo_last_used_idx"),
        ),
    ]
