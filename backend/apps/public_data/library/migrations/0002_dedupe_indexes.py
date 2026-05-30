from django.db import migrations


def drop_index(name: str) -> migrations.RunSQL:
    return migrations.RunSQL(
        f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"',
        reverse_sql=migrations.RunSQL.noop,
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("library", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                drop_index("library_location_gist_idx"),
                drop_index("ix_library_ldong"),
                drop_index("ix_library_adong"),
                drop_index("ix_library_hours_library"),
            ],
            state_operations=[
                migrations.RemoveIndex(model_name="library", name="library_location_gist_idx"),
                migrations.RemoveIndex(model_name="library", name="ix_library_ldong"),
                migrations.RemoveIndex(model_name="library", name="ix_library_adong"),
                migrations.RemoveIndex(model_name="libraryhours", name="ix_library_hours_library"),
            ],
        )
    ]
