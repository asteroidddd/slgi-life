from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("regions", "0007_rename_adjacent_ad_adong_c_c2bcba_idx_adjacent_ad_adong1__7a7873_idx_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="CurrentSeoul",
                    fields=[
                        ("score_rent", models.FloatField(blank=True, null=True)),
                        ("score_amenity", models.FloatField()),
                        ("score_transit", models.FloatField()),
                        ("seoul", models.OneToOneField(db_column="code", on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="current_score", serialize=False, to="regions.seoul")),
                    ],
                    options={"db_table": "current_seoul"},
                ),
                migrations.CreateModel(
                    name="CurrentGu",
                    fields=[
                        ("score_rent", models.FloatField(blank=True, null=True)),
                        ("score_amenity", models.FloatField()),
                        ("score_transit", models.FloatField()),
                        ("gu", models.OneToOneField(db_column="gu_code", on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="current_score", serialize=False, to="regions.gu")),
                    ],
                    options={"db_table": "current_gu"},
                ),
                migrations.CreateModel(
                    name="CurrentLdong",
                    fields=[
                        ("score_rent", models.FloatField(blank=True, null=True)),
                        ("score_amenity", models.FloatField()),
                        ("score_transit", models.FloatField()),
                        ("ldong", models.OneToOneField(db_column="ldong_code", on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="current_score", serialize=False, to="regions.ldong")),
                    ],
                    options={"db_table": "current_ldong"},
                ),
                migrations.CreateModel(
                    name="CurrentAdong",
                    fields=[
                        ("score_rent", models.FloatField(blank=True, null=True)),
                        ("score_amenity", models.FloatField()),
                        ("score_transit", models.FloatField()),
                        ("adong", models.OneToOneField(db_column="adong_code", on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="current_score", serialize=False, to="regions.adong")),
                    ],
                    options={"db_table": "current_adong"},
                ),
            ],
        ),
    ]
