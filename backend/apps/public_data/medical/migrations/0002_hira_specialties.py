# Generated for HIRA medical specialties

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("medical", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicalfacility",
            name="hira_match_method",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AddField(
            model_name="medicalfacility",
            name="hira_match_score",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name="medicalfacility",
            name="hira_synced_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="medicalfacility",
            name="hira_ykiho",
            field=models.CharField(blank=True, help_text="Encrypted HIRA ykiho", max_length=120, null=True),
        ),
        migrations.CreateModel(
            name="MedicalFacilitySpecialty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("specialty_name", models.CharField(max_length=100)),
                ("specialist_count", models.PositiveIntegerField(default=0)),
                (
                    "facility",
                    models.ForeignKey(
                        db_column="hpid",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="specialties",
                        to="medical.medicalfacility",
                    ),
                ),
            ],
            options={
                "db_table": "medical_facility_specialty",
                "verbose_name": "medical facility specialty",
                "verbose_name_plural": "medical facility specialties",
                "unique_together": {("facility", "specialty_name")},
            },
        ),
        migrations.AddIndex(
            model_name="medicalfacility",
            index=models.Index(fields=["hira_ykiho"], name="medical_facility_hira_idx"),
        ),
        migrations.AddIndex(
            model_name="medicalfacilityspecialty",
            index=models.Index(fields=["specialty_name"], name="medical_specialty_name_idx"),
        ),
        migrations.AddIndex(
            model_name="medicalfacilityspecialty",
            index=models.Index(fields=["facility"], name="medical_specialty_hpid_idx"),
        ),
    ]
