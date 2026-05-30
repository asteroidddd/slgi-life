
# Generated for medical amenity source split

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("amenities", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="amenity",
            name="source_table",
            field=models.CharField(
                choices=[
                    ("store", "store"),
                    ("medical_facility", "medical_facility"),
                    ("park", "park"),
                    ("library", "library"),
                    ("univ", "univ"),
                    ("subway_station", "subway_station"),
                    ("bus_stop", "bus_stop"),
                ],
                help_text="Source table name for the amenity row",
                max_length=30,
            ),

        ),
    ]
