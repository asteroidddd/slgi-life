"""sub-plan 2I — BusStop.geom → location 컬럼명 변경.

GistIndex name 갱신:
- busstop_geom_gist_idx → busstop_location_gist_idx
"""

from django.contrib.postgres.indexes import GistIndex
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bus", "0001_initial"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="busstop",
            name="busstop_geom_gist_idx",
        ),
        migrations.RenameField(
            model_name="busstop",
            old_name="geom",
            new_name="location",
        ),
        migrations.AddIndex(
            model_name="busstop",
            index=GistIndex(fields=["location"], name="busstop_location_gist_idx"),
        ),
    ]
