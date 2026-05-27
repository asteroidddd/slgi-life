from django.apps import AppConfig


class ParksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_data.park"
    label = "parks"
    verbose_name = "공원 (Park / ParkAdong / ParkLdong)"
