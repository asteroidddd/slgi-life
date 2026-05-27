from django.apps import AppConfig


class SubwayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_data.subway"
    label = "subway"
    verbose_name = "지하철"
