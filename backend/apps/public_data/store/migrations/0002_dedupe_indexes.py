from django.db import migrations


def drop_index(name: str) -> migrations.RunSQL:
    return migrations.RunSQL(
        f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"',
        reverse_sql=migrations.RunSQL.noop,
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("store", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                drop_index("store_adong_c_b8a0a4_idx"),
                drop_index("store_ldong_c_a49541_idx"),
                drop_index("store_categor_a63bc0_idx"),
                drop_index("store_ksci_co_e67d73_idx"),
                drop_index("store_location_gist_idx"),
            ],
            state_operations=[
                migrations.RemoveIndex(model_name="store", name="store_adong_c_b8a0a4_idx"),
                migrations.RemoveIndex(model_name="store", name="store_ldong_c_a49541_idx"),
                migrations.RemoveIndex(model_name="store", name="store_categor_a63bc0_idx"),
                migrations.RemoveIndex(model_name="store", name="store_ksci_co_e67d73_idx"),
                migrations.RemoveIndex(model_name="store", name="store_location_gist_idx"),
            ],
        )
    ]
