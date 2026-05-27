from django.apps import AppConfig


class HeatmapConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.service.heatmap"
    label = "heatmap"
    verbose_name = "heatmap current scores"
