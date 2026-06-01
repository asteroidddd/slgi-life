from django.urls import path

from .views import (
    MedicalFacilityDetailView,
    MedicalFacilityListView,
    MedicalSpecialtyGroupListView,
    MedicalSpecialtyListView,
)

app_name = "medical_service"

urlpatterns = [
    path("medical/facilities", MedicalFacilityListView.as_view(), name="medical-facilities"),
    path("medical/facilities/<str:hpid>", MedicalFacilityDetailView.as_view(), name="medical-facility-detail"),
    path("medical/specialties", MedicalSpecialtyListView.as_view(), name="medical-specialties"),
    path("medical/specialty-groups", MedicalSpecialtyGroupListView.as_view(), name="medical-specialty-groups"),
]
