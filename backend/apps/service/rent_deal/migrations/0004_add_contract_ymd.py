from django.db import migrations, models


CREATE_TABLE_WITH_CONTRACT_YMD_SQL = """
DROP TABLE IF EXISTS rent_deal_cache;
CREATE TABLE rent_deal_cache (
    id varchar(20) NOT NULL,
    type_code char(1) NOT NULL,
    deposit integer NOT NULL,
    monthly_rent smallint NOT NULL,
    converted_rent smallint NOT NULL,
    area_m2 real NULL,
    lng double precision NULL,
    lat double precision NULL,
    contract_ymd integer NOT NULL
);
"""


CREATE_COMPACT_TABLE_SQL = """
DROP TABLE IF EXISTS rent_deal_cache;
CREATE TABLE rent_deal_cache (
    id varchar(20) NOT NULL,
    type_code char(1) NOT NULL,
    deposit integer NOT NULL,
    monthly_rent smallint NOT NULL,
    converted_rent smallint NOT NULL,
    area_m2 real NULL,
    lng double precision NULL,
    lat double precision NULL
);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("rent_deal_service", "0003_compact_numeric_types"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=CREATE_TABLE_WITH_CONTRACT_YMD_SQL,
                    reverse_sql=CREATE_COMPACT_TABLE_SQL,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="rentdealcache",
                    name="contract_ymd",
                    field=models.IntegerField(help_text="Contract date as YYYYMMDD."),
                ),
            ],
        ),
    ]
