from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.service.rent_deal.updater import rebuild_rent_deal_summary_caches


class Command(BaseCommand):
    help = "Rebuild real-estate map summary caches."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Inspect summary cache state without changing the database.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm destructive summary cache rebuild. Required unless --dry-run is used.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        if not dry_run and not options["yes"]:
            raise CommandError(
                "Refusing to rebuild rent deal summary caches without --yes. "
                "Run --dry-run first, then rerun with --yes."
            )

        stats = rebuild_rent_deal_summary_caches(dry_run=dry_run)
        self.stdout.write(
            json.dumps(
                stats,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
        )
