"""sub-plan 2I — SubwayStation.geom → location 컬럼명 변경.

GistIndex name 갱신:
- subway_geom_gist_idx → subway_location_gist_idx
"""

from django.contrib.postgres.indexes import GistIndex
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("subway", "0001_initial"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="subwaystation",
            name="subway_geom_gist_idx",
        ),
        migrations.RenameField(
            model_name="subwaystation",
            old_name="geom",
            new_name="location",
        ),
        migrations.AddIndex(
            model_name="subwaystation",
            index=GistIndex(fields=["location"], name="subway_location_gist_idx"),
        ),
    ]
