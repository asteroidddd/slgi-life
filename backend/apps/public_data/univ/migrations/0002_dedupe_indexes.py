from django.db import migrations


def drop_index(name: str) -> migrations.RunSQL:
    return migrations.RunSQL(
        f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"',
        reverse_sql=migrations.RunSQL.noop,
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("univ", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                drop_index("univ_boundary_gist_idx"),
                drop_index("univ_location_gist_idx"),
                drop_index("ix_univ_adong_univ"),
                drop_index("ix_univ_adong_adong"),
                drop_index("ix_univ_ldong_univ"),
                drop_index("ix_univ_ldong_ldong"),
            ],
            state_operations=[
                migrations.RemoveIndex(model_name="univ", name="univ_boundary_gist_idx"),
                migrations.RemoveIndex(model_name="univ", name="univ_location_gist_idx"),
                migrations.RemoveIndex(model_name="univadong", name="ix_univ_adong_univ"),
                migrations.RemoveIndex(model_name="univadong", name="ix_univ_adong_adong"),
                migrations.RemoveIndex(model_name="univldong", name="ix_univ_ldong_univ"),
                migrations.RemoveIndex(model_name="univldong", name="ix_univ_ldong_ldong"),
            ],
        )
    ]
