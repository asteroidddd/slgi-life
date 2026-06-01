from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rent_deal", "0002_rent_conversion_rate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rentdeal",
            name="housing_type",
            field=models.CharField(
                choices=[
                    ("아파트", "아파트"),
                    ("연립", "연립"),
                    ("다세대", "다세대"),
                    ("연립다세대", "연립다세대"),
                    ("다가구", "다가구"),
                    ("단독", "단독"),
                    ("단독다가구", "단독다가구"),
                    ("오피스텔", "오피스텔"),
                ],
                help_text="아파트, 연립, 다세대, 연립다세대, 다가구, 단독, 단독다가구, 오피스텔",
                max_length=20,
            ),
        ),
    ]
