from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand

from apps.public_data.rent_deal.models import RentConversionRate
from apps.service.recommend.cache import rebuild_recommend_rent_cache


FALLBACK_MONTHLY_RATE = 0.005


class Command(BaseCommand):
    help = "Rebuild recommendation rent summary cache."

    def add_arguments(self, parser):
        parser.add_argument("--as-of-date", dest="as_of_date", default=None, help="Cache basis date in YYYY-MM-DD.")

    def handle(self, *args, **options):
        row = RentConversionRate.objects.order_by("-period_ym").first()
        monthly_rate = row.monthly_rate if row else FALLBACK_MONTHLY_RATE
        period = row.period_ym if row else ""
        as_of_date = date.fromisoformat(options["as_of_date"]) if options.get("as_of_date") else None
        counts = rebuild_recommend_rent_cache(
            monthly_rate=monthly_rate,
            conversion_rate_period=period,
            as_of_date=as_of_date,
        )
        self.stdout.write(self.style.SUCCESS(f"rebuilt recommend rent cache: {counts}"))
