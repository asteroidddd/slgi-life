from __future__ import annotations

import csv
from pathlib import Path

from django.db import migrations, models


def backfill_specialty_group(apps, schema_editor):
    specialty_model = apps.get_model("medical", "MedicalFacilitySpecialty")
    csv_path = Path(__file__).resolve().parents[4] / "data" / "medical_specialty_groups.csv"
    group_by_name: dict[str, str] = {}
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                name = (row.get("specialty_name") or "").strip()
                group = (row.get("specialty_group") or "").strip()
                if name and group:
                    group_by_name[name] = group
    except FileNotFoundError:
        group_by_name = {}

    for name, group in group_by_name.items():
        specialty_model.objects.filter(specialty_name=name).update(specialty_group=group)
    specialty_model.objects.filter(specialty_group="").update(specialty_group="기타")


class Migration(migrations.Migration):
    dependencies = [
        ("medical", "0004_dedupe_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicalfacilityspecialty",
            name="specialty_group",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddIndex(
            model_name="medicalfacilityspecialty",
            index=models.Index(fields=["specialty_group"], name="medical_specialty_group_idx"),
        ),
        migrations.RunPython(backfill_specialty_group, migrations.RunPython.noop),
    ]
