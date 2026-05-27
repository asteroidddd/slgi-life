"""sub-plan 4.5C — RentDeal.jibun/house_name/contract_type NULL 허용.

schema.dbml line 163~172:
- jibun varchar(50)       NULL 허용 (NOT NULL 미표기)
- house_name varchar(100) NULL 허용 (NOT NULL 미표기)
- contract_type varchar(20) NULL 허용 (NOT NULL 미표기)

DP_DB rent_deal 분포:
- jibun NULL: 2,176,013
- house_name NULL: 2,176,008
- contract_type NULL: 4,528,372

SLGI 적재 시 NotNullViolation 회피.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rent_deal", "0004_rename_rent_deal_ldong_contract_idx_rent_deal_ldong_c_7caf73_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rentdeal",
            name="jibun",
            field=models.CharField(
                blank=True,
                help_text="'법정동 + 지번' 원문 (NULL 허용)",
                max_length=50,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="rentdeal",
            name="house_name",
            field=models.CharField(
                blank=True,
                help_text="건물명 (NULL 허용)",
                max_length=100,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="rentdeal",
            name="contract_type",
            field=models.CharField(
                blank=True,
                help_text="신규, 갱신 (CHECK ck_rent_deal_contract_type, NULL 허용)",
                max_length=20,
                null=True,
            ),
        ),
    ]
