from django.apps import AppConfig


class RentDealConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_data.rent_deal"
    label = "rent_deal"
    verbose_name = "전월세 실거래"
