from django.apps import AppConfig


class RegionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_data.regions"
    label = "regions"
    verbose_name = "행정 단위 (서울/구/법정동) 및 인접·인구"
