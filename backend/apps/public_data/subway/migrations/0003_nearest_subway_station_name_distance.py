from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("subway", "0002_dedupe_indexes"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="nearestsubwayadong",
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name="nearestsubwayldong",
            unique_together=set(),
        ),
        migrations.RemoveConstraint(
            model_name="nearestsubwayadong",
            name="ck_nearest_subway_adong_rank",
        ),
        migrations.RemoveConstraint(
            model_name="nearestsubwayldong",
            name="ck_nearest_subway_ldong_rank",
        ),
        migrations.RemoveField(
            model_name="nearestsubwayadong",
            name="rank",
        ),
        migrations.RemoveField(
            model_name="nearestsubwayldong",
            name="rank",
        ),
        migrations.AlterUniqueTogether(
            name="nearestsubwayadong",
            unique_together={("adong", "station_name")},
        ),
        migrations.AlterUniqueTogether(
            name="nearestsubwayldong",
            unique_together={("ldong", "station_name")},
        ),
    ]
