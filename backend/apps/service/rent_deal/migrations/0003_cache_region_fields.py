from django.db import migrations, models


ADD_COLUMNS_SQL = """
ALTER TABLE rent_deal_cache
    ADD COLUMN IF NOT EXISTS ldong_code varchar(20) NULL,
    ADD COLUMN IF NOT EXISTS adong_code varchar(20) NULL,
    ADD COLUMN IF NOT EXISTS gu_code varchar(20) NULL;
"""

CACHE_MATCH_INDEX_SQL = """
CREATE INDEX CONCURRENTLY IF NOT EXISTS rent_deal_cache_match_filter_idx
    ON rent_deal_cache (type_code, contract_ymd, adong_code)
    INCLUDE (area_m2, converted_rent, deposit, monthly_rent)
    WHERE adong_code IS NOT NULL AND area_m2 IS NOT NULL;
"""

CACHE_GU_INDEX_SQL = """
CREATE INDEX CONCURRENTLY IF NOT EXISTS rent_deal_cache_gu_loc_idx
    ON rent_deal_cache (gu_code)
    WHERE gu_code IS NOT NULL AND lng IS NOT NULL AND lat IS NOT NULL;
"""

SUMMARY_LDONG_INDEX_SQL = """
CREATE INDEX CONCURRENTLY IF NOT EXISTS rent_ldong_type_month_code_idx
    ON rent_deal_ldong_monthly_cache (type_code, year_month, ldong_code);
"""

SUMMARY_GRID_INDEX_SQL = """
CREATE INDEX CONCURRENTLY IF NOT EXISTS rent_grid_type_month_center_idx
    ON rent_deal_grid_monthly_cache (type_code, year_month, center_lng, center_lat);
"""


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("rent_deal_service", "0002_summary_caches"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(ADD_COLUMNS_SQL, reverse_sql=migrations.RunSQL.noop),
                migrations.RunSQL(CACHE_MATCH_INDEX_SQL, reverse_sql=migrations.RunSQL.noop),
                migrations.RunSQL(CACHE_GU_INDEX_SQL, reverse_sql=migrations.RunSQL.noop),
                migrations.RunSQL(SUMMARY_LDONG_INDEX_SQL, reverse_sql=migrations.RunSQL.noop),
                migrations.RunSQL(SUMMARY_GRID_INDEX_SQL, reverse_sql=migrations.RunSQL.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="rentdealcache",
                    name="ldong_code",
                    field=models.CharField(blank=True, max_length=20, null=True),
                ),
                migrations.AddField(
                    model_name="rentdealcache",
                    name="adong_code",
                    field=models.CharField(blank=True, max_length=20, null=True),
                ),
                migrations.AddField(
                    model_name="rentdealcache",
                    name="gu_code",
                    field=models.CharField(blank=True, max_length=20, null=True),
                ),
            ],
        ),
    ]
