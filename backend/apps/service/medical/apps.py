from django.apps import AppConfig


class MedicalServiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.service.medical"
    label = "medical_service"
    verbose_name = "medical service"
