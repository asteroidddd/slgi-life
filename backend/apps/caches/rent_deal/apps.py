from django.apps import AppConfig


class RentDealCacheConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.caches.rent_deal"
    label = "cache_rent_deal"
    verbose_name = "rent deal cache helpers"
