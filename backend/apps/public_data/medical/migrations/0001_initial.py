
# Generated for medical public-data app

import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("regions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MedicalFacility",
            fields=[
                ("hpid", models.CharField(help_text="Facility ID from NMC API (hpid)", max_length=20, primary_key=True, serialize=False)),
                ("type", models.CharField(help_text="Original Korean facility type name", max_length=30)),
                ("name", models.CharField(max_length=200)),
                ("address", models.CharField(max_length=255)),
                ("location", django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
                ("tel1", models.CharField(blank=True, max_length=50, null=True)),
                ("note", models.TextField(blank=True, help_text="Facility note from dutyEtc", null=True)),
                ("adong", models.ForeignKey(blank=True, db_column="adong_code", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="medical_facilities", to="regions.adong")),
                ("ldong", models.ForeignKey(blank=True, db_column="ldong_code", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="medical_facilities", to="regions.ldong")),
            ],
            options={
                "db_table": "medical_facility",
                "verbose_name": "medical facility",
                "verbose_name_plural": "medical facilities",
            },
        ),
        migrations.CreateModel(
            name="MedicalEmergency",
            fields=[
                ("facility", models.OneToOneField(db_column="hpid", on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="emergency", serialize=False, to="medical.medicalfacility")),
                ("phpid", models.CharField(blank=True, max_length=20, null=True)),
                ("emergency_type", models.CharField(blank=True, max_length=100, null=True)),
                ("tel2", models.CharField(blank=True, max_length=50, null=True)),
                ("has_emergency_room", models.BooleanField(default=True)),
                ("note", models.TextField(blank=True, null=True)),
            ],
            options={
                "db_table": "medical_emergency",
                "verbose_name": "medical emergency",
                "verbose_name_plural": "medical emergencies",
            },
        ),
        migrations.CreateModel(
            name="MedicalFacilityHours",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day_type", models.CharField(choices=[("mon", "Monday"), ("tue", "Tuesday"), ("wed", "Wednesday"), ("thu", "Thursday"), ("fri", "Friday"), ("sat", "Saturday"), ("sun", "Sunday"), ("holiday", "Holiday")], max_length=10)),
                ("open_time", models.TimeField(blank=True, null=True)),
                ("close_time", models.TimeField(blank=True, null=True)),
                ("is_closed", models.BooleanField(default=False)),
                ("facility", models.ForeignKey(db_column="hpid", on_delete=django.db.models.deletion.CASCADE, related_name="hours", to="medical.medicalfacility")),
            ],
            options={
                "db_table": "medical_facility_hours",
                "verbose_name": "medical facility hours",
                "verbose_name_plural": "medical facility hours",
                "unique_together": {("facility", "day_type")},
            },
        ),
        migrations.CreateModel(
            name="MedicalHolidayCare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("care_date", models.DateField()),
                ("open_time", models.TimeField(blank=True, null=True)),
                ("close_time", models.TimeField(blank=True, null=True)),
                ("is_closed", models.BooleanField(default=False)),
                ("note", models.TextField(blank=True, help_text="Holiday note from dutyDayetc", null=True)),
                ("facility", models.ForeignKey(db_column="hpid", on_delete=django.db.models.deletion.CASCADE, related_name="holiday_cares", to="medical.medicalfacility")),
            ],
            options={
                "db_table": "medical_holiday_care",
                "verbose_name": "medical holiday care",
                "verbose_name_plural": "medical holiday care",
                "unique_together": {("facility", "care_date")},
            },
        ),
        migrations.AddIndex(model_name="medicalfacility", index=models.Index(fields=["type"], name="medical_facility_type_idx")),
        migrations.AddIndex(model_name="medicalfacility", index=models.Index(fields=["adong"], name="medical_facility_adong_idx")),
        migrations.AddIndex(model_name="medicalfacility", index=models.Index(fields=["ldong"], name="medical_facility_ldong_idx")),
        migrations.AddIndex(model_name="medicalfacility", index=django.contrib.postgres.indexes.GistIndex(fields=["location"], name="medical_facility_location_gist")),
        migrations.AddIndex(model_name="medicalemergency", index=models.Index(fields=["emergency_type"], name="medical_emergency_type_idx")),
        migrations.AddIndex(model_name="medicalfacilityhours", index=models.Index(fields=["day_type"], name="medical_hours_day_idx")),
        migrations.AddIndex(model_name="medicalholidaycare", index=models.Index(fields=["care_date"], name="medical_holiday_date_idx")),
        migrations.AddIndex(model_name="medicalholidaycare", index=models.Index(fields=["facility"], name="medical_holiday_hpid_idx")),
    ]
