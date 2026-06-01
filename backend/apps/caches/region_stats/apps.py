from django.apps import AppConfig


class RegionStatsCacheConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.caches.region_stats"
    label = "cache_region_stats"
    verbose_name = "region stats cache helpers"
