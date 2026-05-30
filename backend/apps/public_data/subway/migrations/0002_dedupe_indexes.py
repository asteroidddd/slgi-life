from django.db import migrations


def drop_index(name: str) -> migrations.RunSQL:
    return migrations.RunSQL(
        f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"',
        reverse_sql=migrations.RunSQL.noop,
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("subway", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                drop_index("subway_location_gist_idx"),
                drop_index("subway_stat_adong_c_77e870_idx"),
                drop_index("subway_stat_ldong_c_9e7181_idx"),
            ],
            state_operations=[
                migrations.RemoveIndex(model_name="subwaystation", name="subway_location_gist_idx"),
                migrations.RemoveIndex(model_name="subwaystation", name="subway_stat_adong_c_77e870_idx"),
                migrations.RemoveIndex(model_name="subwaystation", name="subway_stat_ldong_c_9e7181_idx"),
            ],
        )
    ]
