# Generated manually during Adong naming cleanup.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("parks", "0003_step4_5C_schema_align"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ParkDong",
            new_name="ParkAdong",
        ),
    ]
