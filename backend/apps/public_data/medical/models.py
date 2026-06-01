
from django.contrib.gis.db import models as gis_models
from django.db import models


DAY_TYPE_CHOICES = [
    ("mon", "Monday"),
    ("tue", "Tuesday"),
    ("wed", "Wednesday"),
    ("thu", "Thursday"),
    ("fri", "Friday"),
    ("sat", "Saturday"),
    ("sun", "Sunday"),
    ("holiday", "Holiday"),
]


class MedicalFacility(models.Model):
    hpid = models.CharField(max_length=20, primary_key=True, help_text="Facility ID from NMC API (hpid)")
    type = models.CharField(max_length=30, help_text="Original Korean facility type name")
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=255)
    location = gis_models.PointField(srid=4326, null=True, blank=True)
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medical_facilities",
        db_column="adong_code",
    )
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medical_facilities",
        db_column="ldong_code",
    )
    tel1 = models.CharField(max_length=50, null=True, blank=True)
    note = models.TextField(null=True, blank=True, help_text="Facility note from dutyEtc")

    class Meta:
        db_table = "medical_facility"
        verbose_name = "medical facility"
        verbose_name_plural = "medical facilities"
        indexes = [
            models.Index(fields=["type"], name="medical_facility_type_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.type}] {self.name}"


class MedicalFacilityHours(models.Model):
    facility = models.ForeignKey(
        MedicalFacility,
        on_delete=models.CASCADE,
        related_name="hours",
        db_column="hpid",
    )
    day_type = models.CharField(max_length=10, choices=DAY_TYPE_CHOICES)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        db_table = "medical_facility_hours"
        verbose_name = "medical facility hours"
        verbose_name_plural = "medical facility hours"
        unique_together = [("facility", "day_type")]
        indexes = [models.Index(fields=["day_type"], name="medical_hours_day_idx")]

    def __str__(self) -> str:
        return f"{self.facility_id} {self.day_type}"


class MedicalEmergency(models.Model):
    facility = models.OneToOneField(
        MedicalFacility,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="emergency",
        db_column="hpid",
    )
    phpid = models.CharField(max_length=20, null=True, blank=True)
    emergency_type = models.CharField(max_length=100, null=True, blank=True)
    tel2 = models.CharField(max_length=50, null=True, blank=True)
    has_emergency_room = models.BooleanField(default=True)
    note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "medical_emergency"
        verbose_name = "medical emergency"
        verbose_name_plural = "medical emergencies"
        indexes = [models.Index(fields=["emergency_type"], name="medical_emergency_type_idx")]

    def __str__(self) -> str:
        return f"{self.facility_id} {self.emergency_type or ''}"


class MedicalHolidayCare(models.Model):
    facility = models.ForeignKey(
        MedicalFacility,
        on_delete=models.CASCADE,
        related_name="holiday_cares",
        db_column="hpid",
    )
    care_date = models.DateField()
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    note = models.TextField(null=True, blank=True, help_text="Holiday note from dutyDayetc")

    class Meta:
        db_table = "medical_holiday_care"
        verbose_name = "medical holiday care"
        verbose_name_plural = "medical holiday care"
        unique_together = [("facility", "care_date")]
        indexes = [
            models.Index(fields=["care_date"], name="medical_holiday_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.facility_id} {self.care_date}"



class MedicalHiraMapping(models.Model):
    facility = models.OneToOneField(
        MedicalFacility,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="hira_mapping",
        db_column="hpid",
    )
    hira_ykiho = models.CharField(max_length=120, unique=True, help_text="Encrypted HIRA ykiho")

    class Meta:
        db_table = "medical_hira_mapping"
        verbose_name = "medical HIRA mapping"
        verbose_name_plural = "medical HIRA mappings"

    def __str__(self) -> str:
        return f"{self.facility_id} -> {self.hira_ykiho}"


class MedicalFacilitySpecialty(models.Model):
    mapping = models.ForeignKey(
        MedicalHiraMapping,
        to_field="hira_ykiho",
        db_column="hira_ykiho",
        related_name="specialties",
        on_delete=models.CASCADE,
    )
    specialty_name = models.CharField(max_length=100)
    specialty_group = models.CharField(max_length=50, blank=True, default="")
    specialist_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "medical_facility_specialty"
        verbose_name = "medical facility specialty"
        verbose_name_plural = "medical facility specialties"
        unique_together = [("mapping", "specialty_name")]
        indexes = [
            models.Index(fields=["specialty_name"], name="medical_specialty_name_idx"),
            models.Index(fields=["specialty_group"], name="medical_specialty_group_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.mapping_id} {self.specialty_name}"
