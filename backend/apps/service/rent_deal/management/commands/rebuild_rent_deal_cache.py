from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.service.rent_deal.updater import rebuild_rent_deal_cache


class Command(BaseCommand):
    help = "Rebuild rent_deal_cache from rent_deal."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Inspect source/cache counts without changing the database.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm destructive cache rebuild. Required unless --dry-run is used.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        if not dry_run and not options["yes"]:
            raise CommandError(
                "Refusing to rebuild rent_deal_cache without --yes. "
                "Run --dry-run first, then rerun with --yes."
            )

        stats = rebuild_rent_deal_cache(dry_run=dry_run)
        self.stdout.write(
            json.dumps(
                stats,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
        )
