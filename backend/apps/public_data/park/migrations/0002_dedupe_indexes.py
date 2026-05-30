from django.db import migrations


def drop_index(name: str) -> migrations.RunSQL:
    return migrations.RunSQL(
        f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"',
        reverse_sql=migrations.RunSQL.noop,
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("parks", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                drop_index("park_boundary_gist_idx"),
                drop_index("park_location_gist_idx"),
                drop_index("park_adong_park_id_3c3b3d_idx"),
                drop_index("park_adong_adong_c_30d82b_idx"),
                drop_index("park_ldong_park_id_8414f7_idx"),
                drop_index("park_ldong_ldong_c_385dc6_idx"),
            ],
            state_operations=[
                migrations.RemoveIndex(model_name="park", name="park_boundary_gist_idx"),
                migrations.RemoveIndex(model_name="park", name="park_location_gist_idx"),
                migrations.RemoveIndex(model_name="parkadong", name="park_adong_park_id_3c3b3d_idx"),
                migrations.RemoveIndex(model_name="parkadong", name="park_adong_adong_c_30d82b_idx"),
                migrations.RemoveIndex(model_name="parkldong", name="park_ldong_park_id_8414f7_idx"),
                migrations.RemoveIndex(model_name="parkldong", name="park_ldong_ldong_c_385dc6_idx"),
            ],
        )
    ]
