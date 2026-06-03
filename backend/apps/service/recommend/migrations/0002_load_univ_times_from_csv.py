from django.db import migrations


def load_univ_times_from_csv(apps, schema_editor):
    from apps.service.recommend.univ_time_loader import import_univ_times_from_csv

    import_univ_times_from_csv()


class Migration(migrations.Migration):

    dependencies = [
        ("recommend", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_univ_times_from_csv, reverse_code=migrations.RunPython.noop),
    ]
