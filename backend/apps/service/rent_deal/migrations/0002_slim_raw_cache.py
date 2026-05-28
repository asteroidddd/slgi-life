from django.db import migrations, models


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


CREATE_INITIAL_TABLE_SQL = """
DROP TABLE IF EXISTS rent_deal_cache;
CREATE TABLE rent_deal_cache (
    id varchar(60) PRIMARY KEY,
    housing_type varchar(10) NOT NULL,
    deposit integer NOT NULL,
    monthly_rent integer NOT NULL,
    converted_rent double precision NOT NULL,
    area_m2 double precision NULL,
    location geometry(Point, 4326) NULL
);
CREATE INDEX rent_cache_type_idx ON rent_deal_cache (housing_type);
CREATE INDEX rent_cache_conv_idx ON rent_deal_cache (converted_rent);
CREATE INDEX rent_cache_area_idx ON rent_deal_cache (area_m2);
CREATE INDEX rent_cache_loc_gist_idx ON rent_deal_cache USING gist (location);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("rent_deal_service", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=CREATE_SLIM_TABLE_SQL,
                    reverse_sql=CREATE_INITIAL_TABLE_SQL,
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
                                max_length=60,
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
                            models.IntegerField(
                                help_text="Monthly rent in KRW 10,000 units."
                            ),
                        ),
                        (
                            "converted_rent",
                            models.FloatField(
                                help_text=(
                                    "Monthly rent plus deposit conversion, "
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
