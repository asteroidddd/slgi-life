from django.apps import AppConfig


class LegacyNeighborhoodsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.legacy.neighborhoods"
    label = "neighborhoods"
    verbose_name = "Legacy neighborhoods migration anchor"
