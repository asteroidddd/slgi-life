from django.db import migrations, models


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


CREATE_SLIM_TABLE_SQL = """
DROP TABLE IF EXISTS rent_deal_cache;
CREATE TABLE rent_deal_cache (
    id varchar(60) NOT NULL,
    type_code char(1) NOT NULL,
    deposit integer NOT NULL,
    monthly_rent integer NOT NULL,
    converted_rent double precision NOT NULL,
    area_m2 double precision NULL,
    lng double precision NULL,
    lat double precision NULL
);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("rent_deal_service", "0002_slim_raw_cache"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=CREATE_COMPACT_TABLE_SQL,
                    reverse_sql=CREATE_SLIM_TABLE_SQL,
                ),
            ],
            state_operations=[
                migrations.DeleteModel(name="RentDealCache"),
                migrations.CreateModel(
                    name="RentDealCache",
                    fields=[
                        (
                            "id",
                            models.CharField(
                                max_length=20,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        ("type_code", models.CharField(max_length=1)),
                        (
                            "deposit",
                            models.IntegerField(
                                help_text="Deposit amount in KRW 10,000 units."
                            ),
                        ),
                        (
                            "monthly_rent",
                            models.SmallIntegerField(
                                help_text="Monthly rent in KRW 10,000 units."
                            ),
                        ),
                        (
                            "converted_rent",
                            models.SmallIntegerField(
                                help_text=(
                                    "Rounded monthly rent plus deposit conversion, "
                                    "in KRW 10,000 units."
                                )
                            ),
                        ),
                        ("area_m2", models.FloatField(blank=True, null=True)),
                        ("lng", models.FloatField(blank=True, null=True)),
                        ("lat", models.FloatField(blank=True, null=True)),
                    ],
                    options={
                        "managed": False,
                        "db_table": "rent_deal_cache",
                        "verbose_name": "rent deal cache",
                        "verbose_name_plural": "rent deal caches",
                    },
                ),
            ],
        ),
    ]
