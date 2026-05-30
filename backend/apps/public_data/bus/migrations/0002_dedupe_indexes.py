from django.db import migrations


def drop_index(name: str) -> migrations.RunSQL:
    return migrations.RunSQL(
        f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"',
        reverse_sql=migrations.RunSQL.noop,
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("bus", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                drop_index("bus_stop_adong_c_711295_idx"),
                drop_index("bus_stop_ldong_c_33a3d6_idx"),
                drop_index("busstop_location_gist_idx"),
            ],
            state_operations=[
                migrations.RemoveIndex(model_name="busstop", name="bus_stop_adong_c_711295_idx"),
                migrations.RemoveIndex(model_name="busstop", name="bus_stop_ldong_c_33a3d6_idx"),
                migrations.RemoveIndex(model_name="busstop", name="busstop_location_gist_idx"),
            ],
        )
    ]
