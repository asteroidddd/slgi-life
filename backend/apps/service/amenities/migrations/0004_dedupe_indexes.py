from django.db import migrations


def drop_index(name: str) -> migrations.RunSQL:
    return migrations.RunSQL(
        f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"',
        reverse_sql=migrations.RunSQL.noop,
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("amenities", "0003_add_study_cafe_category"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                drop_index("amenity_location_gist_idx"),
                drop_index("amenity_ado_amenity_5d63e4_idx"),
                drop_index("amenity_ado_adong_c_7226c7_idx"),
                drop_index("amenity_ldo_amenity_6c118b_idx"),
                drop_index("amenity_ldo_ldong_c_9dfdd4_idx"),
            ],
            state_operations=[
                migrations.RemoveIndex(model_name="amenity", name="amenity_location_gist_idx"),
                migrations.RemoveIndex(model_name="amenityadong", name="amenity_ado_amenity_5d63e4_idx"),
                migrations.RemoveIndex(model_name="amenityadong", name="amenity_ado_adong_c_7226c7_idx"),
                migrations.RemoveIndex(model_name="amenityldong", name="amenity_ldo_amenity_6c118b_idx"),
                migrations.RemoveIndex(model_name="amenityldong", name="amenity_ldo_ldong_c_9dfdd4_idx"),
            ],
        )
    ]
