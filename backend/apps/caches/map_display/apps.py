from __future__ import annotations

from django.apps import AppConfig


class MapDisplayCacheConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.caches.map_display"
    verbose_name = "Map display caches"
