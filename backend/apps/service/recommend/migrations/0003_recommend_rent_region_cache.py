from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recommend", "0002_load_univ_times_from_csv"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendRentRegionCache",
            fields=[
                ("cache_key", models.CharField(max_length=120, primary_key=True, serialize=False)),
                ("region_type", models.CharField(max_length=10)),
                ("region_code", models.CharField(max_length=20)),
                ("scope", models.CharField(default="recent_365d", max_length=20)),
                ("as_of_date", models.DateField()),
                ("recent_from", models.DateField()),
                ("conversion_rate_period", models.CharField(blank=True, default="", max_length=20)),
                ("monthly_rate", models.FloatField()),
                ("deal_count", models.PositiveIntegerField(default=0)),
                ("avg_per_m2", models.FloatField(blank=True, null=True)),
                ("median_converted", models.FloatField(blank=True, null=True)),
                ("min_contract_date", models.DateField(blank=True, null=True)),
                ("max_contract_date", models.DateField(blank=True, null=True)),
                ("source_version", models.CharField(blank=True, default="", max_length=40)),
                ("computed_at", models.DateTimeField()),
            ],
            options={
                "verbose_name": "recommend rent region cache",
                "verbose_name_plural": "recommend rent region caches",
                "db_table": "recommend_rent_region_cache",
            },
        ),
        migrations.AddConstraint(
            model_name="recommendrentregioncache",
            constraint=models.UniqueConstraint(
                fields=("region_type", "region_code", "scope", "as_of_date", "conversion_rate_period"),
                name="uq_recommend_rent_region_cache",
            ),
        ),
        migrations.AddIndex(
            model_name="recommendrentregioncache",
            index=models.Index(fields=["region_type", "scope", "as_of_date"], name="recommend_rent_scope_idx"),
        ),
        migrations.AddIndex(
            model_name="recommendrentregioncache",
            index=models.Index(fields=["region_type", "region_code"], name="recommend_rent_region_idx"),
        ),
        migrations.AddIndex(
            model_name="recommendrentregioncache",
            index=models.Index(fields=["source_version"], name="recommend_rent_source_idx"),
        ),
    ]
