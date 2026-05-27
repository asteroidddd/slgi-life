from django.apps import AppConfig


class UnivConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_data.univ"
    label = "univ"
    verbose_name = "대학"
