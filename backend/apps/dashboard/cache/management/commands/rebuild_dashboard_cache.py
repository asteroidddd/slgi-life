from django.core.management.base import BaseCommand, CommandError

from apps.dashboard.cache.updater import update_all


class Command(BaseCommand):
    help = "Rebuild dashboard JSON caches for adong/ldong regions with bulk SQL."

    def add_arguments(self, parser):
        parser.add_argument("--region-type", choices=["all", "adong", "ldong"], default="all")
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete existing cache rows for selected region type before rebuild.",
        )

    def handle(self, *args, **options):
        region_type = options["region_type"]
        limit = options.get("limit")
        offset = options.get("offset") or 0
        truncate = bool(options.get("truncate"))

        if region_type == "all" and (limit is not None or offset):
            raise CommandError("--limit/--offset requires --region-type adong or ldong.")

        results = update_all(region_type=region_type, limit=limit, offset=offset, truncate=truncate)
        ok = sum(1 for item in results if item.ok)
        failed = [item for item in results if not item.ok]
        for item in failed[:20]:
            self.stderr.write(f"{item.region_type}:{item.slug or item.code} failed: {item.error}")
        self.stdout.write(self.style.SUCCESS(f"dashboard cache rebuilt: ok={ok}, failed={len(failed)}"))
        if failed:
            raise CommandError(f"{len(failed)} dashboard cache rows failed.")
