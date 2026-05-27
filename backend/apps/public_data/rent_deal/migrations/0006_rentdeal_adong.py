# Generated for rent_deal adong mapping on 2026-05-20.

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("regions", "0007_rename_adjacent_ad_adong_c_c2bcba_idx_adjacent_ad_adong1__7a7873_idx_and_more"),
        ("rent_deal", "0005_step4_5C_text_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="rentdeal",
            name="adong",
            field=models.ForeignKey(
                blank=True,
                db_column="adong_code",
                help_text="행정동. 확실한 ldong 포함/동일 또는 신뢰 가능한 위치 매핑만 저장.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="rent_deals",
                to="regions.adong",
            ),
        ),
        migrations.AddIndex(
            model_name="rentdeal",
            index=models.Index(
                fields=["adong", "contract_date"],
                name="rent_deal_adong_contract_idx",
            ),
        ),
        migrations.AlterField(
            model_name="rentdeal",
            name="location",
            field=django.contrib.gis.db.models.fields.PointField(
                blank=True,
                help_text="지번 보유 행의 외부 지오코딩 API 결과. 단독/다가구 또는 신뢰 불가 좌표는 NULL.",
                null=True,
                srid=4326,
            ),
        ),
    ]
