from django.apps import AppConfig


class RentDealServiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.service.rent_deal"
    label = "rent_deal_service"
    verbose_name = "rent deal service"
