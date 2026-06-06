from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.caches.map_display.updater import (
    rebuild_map_amenity_marker_cache,
    rebuild_map_medical_marker_cache,
)


class Command(BaseCommand):
    help = "Rebuild lightweight map marker cache tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            choices=("all", "amenity", "medical"),
            default="all",
            help="Cache target to rebuild.",
        )

    def handle(self, *args, **options):
        target = options["target"]
        if target in {"all", "amenity"}:
            self.stdout.write(f"amenity markers: {rebuild_map_amenity_marker_cache()}")
        if target in {"all", "medical"}:
            self.stdout.write(f"medical markers: {rebuild_map_medical_marker_cache()}")
