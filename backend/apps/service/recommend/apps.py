from django.apps import AppConfig


class RecommendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.service.recommend"
    label = "recommend"
    verbose_name = "조건 추천"
