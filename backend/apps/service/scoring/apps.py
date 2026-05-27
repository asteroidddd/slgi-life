from django.apps import AppConfig


class ScoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.service.scoring"
    label = "scoring"
    verbose_name = "단위별 최신 score"
