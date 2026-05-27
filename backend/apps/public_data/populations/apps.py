from django.apps import AppConfig


class PopulationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_data.populations"
    label = "populations"
    verbose_name = "단위별 인구"
