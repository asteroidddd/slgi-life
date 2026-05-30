from django.db import migrations


def drop_index(name: str) -> migrations.RunSQL:
    return migrations.RunSQL(
        f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"',
        reverse_sql=migrations.RunSQL.noop,
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("medical", "0003_hira_mapping_cache"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                drop_index("medical_facility_adong_idx"),
                drop_index("medical_facility_ldong_idx"),
                drop_index("medical_facility_location_gist"),
                drop_index("medical_holiday_hpid_idx"),
                drop_index("medical_specialty_ykiho_idx"),
            ],
            state_operations=[
                migrations.RemoveIndex(model_name="medicalfacility", name="medical_facility_adong_idx"),
                migrations.RemoveIndex(model_name="medicalfacility", name="medical_facility_ldong_idx"),
                migrations.RemoveIndex(model_name="medicalfacility", name="medical_facility_location_gist"),
                migrations.RemoveIndex(model_name="medicalholidaycare", name="medical_holiday_hpid_idx"),
                migrations.RemoveIndex(model_name="medicalfacilityspecialty", name="medical_specialty_ykiho_idx"),
            ],
        )
    ]
