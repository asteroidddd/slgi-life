from pathlib import Path

from django.core.management.base import BaseCommand

from apps.service.recommend.univ_time_loader import import_univ_times_from_csv


class Command(BaseCommand):
    help = "Import adong/ldong university travel-time CSV files into recommendation tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=Path,
            default=None,
            help="Directory containing adong_univ_time.csv and ldong_univ_time.csv.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate CSV and DB code matching without replacing table rows.",
        )

    def handle(self, *args, **options):
        summary = import_univ_times_from_csv(
            data_dir=options["data_dir"],
            dry_run=options["dry_run"],
        )
        mode = "validated" if summary.dry_run else "imported"
        self.stdout.write(
            self.style.SUCCESS(
                (
                    f"University travel times {mode}: "
                    f"adong_rows={summary.adong_rows}, "
                    f"ldong_rows={summary.ldong_rows}, "
                    f"adong_codes={summary.adong_codes}, "
                    f"ldong_codes={summary.ldong_codes}, "
                    f"univ_codes={summary.univ_codes}"
                )
            )
        )
