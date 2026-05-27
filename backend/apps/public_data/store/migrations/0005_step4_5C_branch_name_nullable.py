"""sub-plan 4.5C — Store.branch_name NULL 허용.

schema.dbml line 184 'branch_name varchar(100)' NULL 허용 (NOT NULL 미표기).
DP_DB store 487,041행에 branch_name NULL → SLGI 적재 시 NotNullViolation 회피.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0004_rename_store_adong_idx_store_adong_c_b8a0a4_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="store",
            name="branch_name",
            field=models.CharField(
                blank=True,
                help_text="지점명 (schema.dbml NULL 허용)",
                max_length=100,
                null=True,
            ),
        ),
    ]
