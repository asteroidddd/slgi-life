from django.apps import AppConfig


class PreferenceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.service.preference"
    label = "preference"
    verbose_name = "Preference"
