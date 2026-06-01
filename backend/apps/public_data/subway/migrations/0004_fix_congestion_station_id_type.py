from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("subway", "0003_nearest_subway_station_name_distance"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE subway_congestion
                ALTER COLUMN station_id TYPE varchar(20)
                USING station_id::text;

            ALTER TABLE subway_congestion
                ADD CONSTRAINT subway_congestion_station_id_fk
                FOREIGN KEY (station_id)
                REFERENCES subway_station(id)
                ON DELETE CASCADE
                DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE subway_congestion
                DROP CONSTRAINT IF EXISTS subway_congestion_station_id_fk;

            ALTER TABLE subway_congestion
                ALTER COLUMN station_id TYPE bigint
                USING station_id::bigint;
            """,
        ),
    ]
