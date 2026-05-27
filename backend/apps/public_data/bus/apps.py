from django.apps import AppConfig


class BusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_data.bus"
    label = "bus"
    verbose_name = "버스"
