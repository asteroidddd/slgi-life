from django.apps import AppConfig


class MedicalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_data.medical"
    label = "medical"
    verbose_name = "medical public data"
