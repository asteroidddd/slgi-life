"""sub-plan 4.5C — BusStop.stop_number NULL 허용.

schema.dbml line 245 'stop_number varchar(20)' NULL 허용 (NOT NULL 미표기).
DP_DB bus_stop 1,559행에 stop_number NULL → SLGI 적재 시 NotNullViolation 회피.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bus", "0004_rename_bus_stop_adong_idx_bus_stop_adong_c_711295_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="busstop",
            name="stop_number",
            field=models.CharField(
                blank=True,
                help_text=(
                    "정류소번호 (서울 BIS arsId). RDS bus_stop.stop_number 1:1. "
                    "schema.dbml NULL 허용 (line 245)."
                ),
                max_length=20,
                null=True,
            ),
        ),
    ]
