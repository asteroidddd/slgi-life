"""sub-plan 2I — RentDeal.geom → location 컬럼명 변경.

GistIndex name 갱신:
- rentdeal_geom_gist_idx → rentdeal_location_gist_idx
"""

from django.contrib.postgres.indexes import GistIndex
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rent_deal", "0001_initial"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="rentdeal",
            name="rentdeal_geom_gist_idx",
        ),
        migrations.RenameField(
            model_name="rentdeal",
            old_name="geom",
            new_name="location",
        ),
        migrations.AddIndex(
            model_name="rentdeal",
            index=GistIndex(fields=["location"], name="rentdeal_location_gist_idx"),
        ),
    ]
