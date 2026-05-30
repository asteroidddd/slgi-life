from django.db import migrations, models


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS rent_deal_ldong_monthly_cache (
    cache_key varchar(40) NOT NULL,
    ldong_code varchar(20) NOT NULL,
    ldong_name varchar(100) NOT NULL,
    gu_code varchar(20) NOT NULL,
    gu_name varchar(100) NOT NULL,
    year_month integer NOT NULL,
    type_code char(1) NOT NULL,
    avg_converted_rent smallint NOT NULL,
    deal_count integer NOT NULL,
    center_lng double precision NULL,
    center_lat double precision NULL
);

CREATE TABLE IF NOT EXISTS rent_deal_grid_monthly_cache (
    cache_key varchar(48) NOT NULL,
    grid_id varchar(32) NOT NULL,
    grid_size_m smallint NOT NULL DEFAULT 300,
    gu_code varchar(20) NOT NULL,
    gu_name varchar(100) NOT NULL,
    year_month integer NOT NULL,
    type_code char(1) NOT NULL,
    avg_converted_rent smallint NOT NULL,
    deal_count integer NOT NULL,
    center_lng double precision NULL,
    center_lat double precision NULL
);

CREATE INDEX IF NOT EXISTS rent_ldong_month_type_idx
    ON rent_deal_ldong_monthly_cache (year_month, type_code);
CREATE INDEX IF NOT EXISTS rent_ldong_code_idx
    ON rent_deal_ldong_monthly_cache (ldong_code);
CREATE INDEX IF NOT EXISTS rent_grid_month_type_idx
    ON rent_deal_grid_monthly_cache (year_month, type_code);
CREATE INDEX IF NOT EXISTS rent_grid_gu_idx
    ON rent_deal_grid_monthly_cache (gu_code);
CREATE INDEX IF NOT EXISTS rent_grid_center_idx
    ON rent_deal_grid_monthly_cache (center_lng, center_lat);
"""

DROP_SQL = """
DROP TABLE IF EXISTS rent_deal_grid_monthly_cache;
DROP TABLE IF EXISTS rent_deal_ldong_monthly_cache;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("rent_deal_service", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(CREATE_SQL, reverse_sql=DROP_SQL),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="RentDealLdongMonthlyCache",
                    fields=[
                        ("cache_key", models.CharField(max_length=40, primary_key=True, serialize=False)),
                        ("ldong_code", models.CharField(max_length=20)),
                        ("ldong_name", models.CharField(max_length=100)),
                        ("gu_code", models.CharField(max_length=20)),
                        ("gu_name", models.CharField(max_length=100)),
                        ("year_month", models.IntegerField(help_text="Contract month as YYYYMM.")),
                        ("type_code", models.CharField(max_length=1)),
                        (
                            "avg_converted_rent",
                            models.SmallIntegerField(help_text="Average converted rent in KRW 10,000 units."),
                        ),
                        ("deal_count", models.IntegerField()),
                        ("center_lng", models.FloatField(blank=True, null=True)),
                        ("center_lat", models.FloatField(blank=True, null=True)),
                    ],
                    options={
                        "verbose_name": "rent deal ldong monthly cache",
                        "verbose_name_plural": "rent deal ldong monthly caches",
                        "db_table": "rent_deal_ldong_monthly_cache",
                        "managed": False,
                    },
                ),
                migrations.CreateModel(
                    name="RentDealGridMonthlyCache",
                    fields=[
                        ("cache_key", models.CharField(max_length=48, primary_key=True, serialize=False)),
                        ("grid_id", models.CharField(max_length=32)),
                        ("grid_size_m", models.SmallIntegerField(default=300)),
                        ("gu_code", models.CharField(max_length=20)),
                        ("gu_name", models.CharField(max_length=100)),
                        ("year_month", models.IntegerField(help_text="Contract month as YYYYMM.")),
                        ("type_code", models.CharField(max_length=1)),
                        (
                            "avg_converted_rent",
                            models.SmallIntegerField(help_text="Average converted rent in KRW 10,000 units."),
                        ),
                        ("deal_count", models.IntegerField()),
                        ("center_lng", models.FloatField(blank=True, null=True)),
                        ("center_lat", models.FloatField(blank=True, null=True)),
                    ],
                    options={
                        "verbose_name": "rent deal grid monthly cache",
                        "verbose_name_plural": "rent deal grid monthly caches",
                        "db_table": "rent_deal_grid_monthly_cache",
                        "managed": False,
                    },
                ),
            ],
        ),
    ]
