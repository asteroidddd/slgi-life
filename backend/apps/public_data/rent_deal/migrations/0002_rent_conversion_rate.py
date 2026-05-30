from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rent_deal", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RentConversionRate",
            fields=[
                ("period_ym", models.CharField(help_text="KOSIS PRD_DE as YYYYMM", max_length=6, primary_key=True, serialize=False)),
                ("annual_rate", models.DecimalField(decimal_places=3, help_text="Annual conversion rate, percent.", max_digits=7)),
                ("source", models.CharField(default="KOSIS \ud55c\uad6d\ubd80\ub3d9\uc0b0\uc6d0 \uc804\uc6d4\uc138\uc804\ud658\uc728", max_length=100)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("fetched_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "rent_conversion_rate",
                "verbose_name": "rent conversion rate",
                "verbose_name_plural": "rent conversion rates",
                "ordering": ["-period_ym"],
            },
        ),
    ]
