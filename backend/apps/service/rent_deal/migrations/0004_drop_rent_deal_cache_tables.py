from django.db import migrations


DROP_SQL = """
DROP TABLE IF EXISTS rent_deal_grid_monthly_cache;
DROP TABLE IF EXISTS rent_deal_ldong_monthly_cache;
DROP TABLE IF EXISTS rent_deal_cache;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("rent_deal_service", "0003_cache_region_fields"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(DROP_SQL, reverse_sql=migrations.RunSQL.noop),
            ],
            state_operations=[
                migrations.DeleteModel(name="RentDealGridMonthlyCache"),
                migrations.DeleteModel(name="RentDealLdongMonthlyCache"),
                migrations.DeleteModel(name="RentDealCache"),
            ],
        ),
    ]
