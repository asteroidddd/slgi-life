from django.contrib.gis.db import models as gis_models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_favorite_dong_to_adong"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="address",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="user",
            name="home_location",
            field=gis_models.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name="user",
            name="address_geocode_status",
            field=models.CharField(blank=True, default="not_provided", max_length=20),
        ),
        migrations.AddField(
            model_name="user",
            name="address_geocode_error",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS user_preference CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
