from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_data.store"
    label = "store"
    verbose_name = "상가"
