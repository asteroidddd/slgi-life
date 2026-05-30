import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("regions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DashboardAdongCache",
            fields=[
                ("region_payload", models.JSONField(default=dict)),
                ("intro", models.TextField(blank=True, default="")),
                ("rent_summary", models.JSONField(default=dict)),
                ("transit_summary", models.JSONField(default=dict)),
                ("infra_summary", models.JSONField(default=dict)),
                ("safety_summary", models.JSONField(default=dict)),
                ("dashboard_payload", models.JSONField(default=dict)),
                ("source_version", models.CharField(blank=True, default="", max_length=40)),
                ("computed_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "adong",
                    models.OneToOneField(
                        db_column="adong_code",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="dashboard_cache",
                        serialize=False,
                        to="regions.adong",
                    ),
                ),
            ],
            options={
                "verbose_name": "dashboard adong cache",
                "verbose_name_plural": "dashboard adong caches",
                "db_table": "dashboard_adong_cache",
            },
        ),
        migrations.CreateModel(
            name="DashboardLdongCache",
            fields=[
                ("region_payload", models.JSONField(default=dict)),
                ("intro", models.TextField(blank=True, default="")),
                ("rent_summary", models.JSONField(default=dict)),
                ("transit_summary", models.JSONField(default=dict)),
                ("infra_summary", models.JSONField(default=dict)),
                ("safety_summary", models.JSONField(default=dict)),
                ("dashboard_payload", models.JSONField(default=dict)),
                ("source_version", models.CharField(blank=True, default="", max_length=40)),
                ("computed_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "ldong",
                    models.OneToOneField(
                        db_column="ldong_code",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="dashboard_cache",
                        serialize=False,
                        to="regions.ldong",
                    ),
                ),
            ],
            options={
                "verbose_name": "dashboard ldong cache",
                "verbose_name_plural": "dashboard ldong caches",
                "db_table": "dashboard_ldong_cache",
            },
        ),
    ]
