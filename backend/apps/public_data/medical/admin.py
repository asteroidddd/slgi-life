from django.contrib import admin

from .models import MedicalEmergency, MedicalFacility, MedicalFacilityHours, MedicalFacilitySpecialty, MedicalHiraMapping, MedicalHolidayCare


@admin.register(MedicalFacility)
class MedicalFacilityAdmin(admin.ModelAdmin):
    list_display = ("hpid", "type", "name", "tel1")
    search_fields = ("hpid", "name", "address")
    list_filter = ("type",)


@admin.register(MedicalFacilityHours)
class MedicalFacilityHoursAdmin(admin.ModelAdmin):
    list_display = ("facility_id", "day_type", "open_time", "close_time", "is_closed")
    list_filter = ("day_type", "is_closed")


@admin.register(MedicalEmergency)
class MedicalEmergencyAdmin(admin.ModelAdmin):
    list_display = ("facility_id", "emergency_type", "tel2", "has_emergency_room")
    search_fields = ("facility_id", "facility__name", "emergency_type")


@admin.register(MedicalHolidayCare)
class MedicalHolidayCareAdmin(admin.ModelAdmin):
    list_display = ("facility_id", "care_date", "open_time", "close_time", "is_closed")
    list_filter = ("care_date", "is_closed")


@admin.register(MedicalHiraMapping)
class MedicalHiraMappingAdmin(admin.ModelAdmin):
    list_display = ("facility_id", "hira_ykiho")
    search_fields = ("facility_id", "facility__name", "hira_ykiho")


@admin.register(MedicalFacilitySpecialty)
class MedicalFacilitySpecialtyAdmin(admin.ModelAdmin):
    list_display = ("mapping_id", "specialty_name", "specialist_count")
    search_fields = ("mapping_id", "specialty_name")
    list_filter = ("specialty_name",)

