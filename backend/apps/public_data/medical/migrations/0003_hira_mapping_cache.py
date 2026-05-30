# Generated for medical HIRA mapping cache restructure

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("medical", "0002_hira_specialties"),
    ]

    operations = [
        migrations.DeleteModel(name="MedicalFacilitySpecialty"),
        migrations.RemoveIndex(model_name="medicalfacility", name="medical_facility_hira_idx"),
        migrations.RemoveField(model_name="medicalfacility", name="hira_match_method"),
        migrations.RemoveField(model_name="medicalfacility", name="hira_match_score"),
        migrations.RemoveField(model_name="medicalfacility", name="hira_synced_at"),
        migrations.RemoveField(model_name="medicalfacility", name="hira_ykiho"),
        migrations.CreateModel(
            name="MedicalHiraMapping",
            fields=[
                (
                    "facility",
                    models.OneToOneField(
                        db_column="hpid",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="hira_mapping",
                        serialize=False,
                        to="medical.medicalfacility",
                    ),
                ),
                ("hira_ykiho", models.CharField(help_text="Encrypted HIRA ykiho", max_length=120, unique=True)),
            ],
            options={
                "db_table": "medical_hira_mapping",
                "verbose_name": "medical HIRA mapping",
                "verbose_name_plural": "medical HIRA mappings",
            },
        ),
        migrations.CreateModel(
            name="MedicalFacilitySpecialty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("specialty_name", models.CharField(max_length=100)),
                ("specialist_count", models.PositiveIntegerField(default=0)),
                (
                    "mapping",
                    models.ForeignKey(
                        db_column="hira_ykiho",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="specialties",
                        to="medical.medicalhiramapping",
                        to_field="hira_ykiho",
                    ),
                ),
            ],
            options={
                "db_table": "medical_facility_specialty",
                "verbose_name": "medical facility specialty",
                "verbose_name_plural": "medical facility specialties",
                "unique_together": {("mapping", "specialty_name")},
            },
        ),
        migrations.AddIndex(
            model_name="medicalfacilityspecialty",
            index=models.Index(fields=["specialty_name"], name="medical_specialty_name_idx"),
        ),
        migrations.AddIndex(
            model_name="medicalfacilityspecialty",
            index=models.Index(fields=["mapping"], name="medical_specialty_ykiho_idx"),
        ),
    ]
