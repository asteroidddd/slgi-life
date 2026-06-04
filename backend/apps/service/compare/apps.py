from django.apps import AppConfig


class CompareConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.service.compare"
    label = "compare_service"
    verbose_name = "neighborhood compare service"
