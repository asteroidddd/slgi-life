import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0002_dedupe_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="DaisoStore",
            fields=[
                ("id", models.CharField(help_text="Stable Daiso store id", max_length=64, primary_key=True, serialize=False)),
                ("name", models.CharField(help_text="Daiso store name", max_length=200)),
                ("address", models.CharField(help_text="Store address", max_length=255)),
                ("location", django.contrib.gis.db.models.fields.PointField(help_text="Store location (WGS84)", srid=4326)),
            ],
            options={
                "verbose_name": "Daiso store",
                "verbose_name_plural": "Daiso stores",
                "db_table": "daiso_store",
                "ordering": ["name", "address"],
                "indexes": [
                    django.contrib.postgres.indexes.GistIndex(fields=["location"], name="daiso_store_location_gist_idx"),
                ],
            },
        ),
    ]
