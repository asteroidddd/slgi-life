"""Run public-data updaters."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _django import setup  # noqa: E402

setup()

from apps.public_data.exceptions import RateLimitedError  # noqa: E402
from apps.public_data.bus.updater import BusUpdateOptions, update as update_bus  # noqa: E402
from apps.public_data.library.updater import (  # noqa: E402
    LibraryUpdateOptions,
    update as update_library,
)
from apps.public_data.metrics.updater import (  # noqa: E402
    MetricsUpdateOptions,
    update as update_metrics,
)
from apps.public_data.park.updater import ParksUpdateOptions, update as update_parks  # noqa: E402
from apps.public_data.populations.updater import (  # noqa: E402
    PopulationsUpdateOptions,
    update as update_populations,
)
from apps.public_data.regions.updater import RegionsUpdateOptions, update as update_regions  # noqa: E402
from apps.public_data.rent_deal.updater import (  # noqa: E402
    RentDealsUpdateOptions,
    update as update_rent_deals,
)
from apps.public_data.store.updater import StoresUpdateOptions, update as update_stores  # noqa: E402
from apps.public_data.subway.updater import SubwayUpdateOptions, update as update_subway  # noqa: E402
from apps.public_data.univ.updater import UnivUpdateOptions, update as update_univ  # noqa: E402


DATASET_ORDER = (
    "regions",
    "metrics",
    "populations",
    "rent_deals",
    "univ",
    "bus",
    "subway",
    "stores",
    "parks",
    "library",
)
UNSUCCESSFUL_STATUSES = {"rate_limited", "partial", "failed", "error"}


def _date(value: str | None):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _contains_rate_limited(value) -> bool:
    if isinstance(value, dict):
        if value.get("status") == "rate_limited":
            return True
        return any(_contains_rate_limited(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_rate_limited(item) for item in value)
    return False


def _contains_unsuccessful(value) -> bool:
    if isinstance(value, dict):
        if value.get("error"):
            return True
        if value.get("completed") is False:
            return True
        if value.get("status") in UNSUCCESSFUL_STATUSES:
            return True
        return any(_contains_unsuccessful(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_unsuccessful(item) for item in value)
    return False


def _unsuccessful_status(value) -> str:
    if _contains_rate_limited(value):
        return "rate_limited"
    return "partial"


def _run_dataset(dataset: str, args: argparse.Namespace, *, dry_run: bool) -> dict:
    if dataset == "regions":
        return update_regions(
            RegionsUpdateOptions(
                dry_run=dry_run,
                force=args.force,
                limit=args.limit,
            )
        )
    if dataset == "bus":
        return update_bus(
            BusUpdateOptions(
                dry_run=dry_run,
                update_stops=not args.skip_stops,
                update_congestion=not args.skip_congestion,
                start_date=_date(args.start_date),
                end_date=_date(args.end_date),
                limit=args.limit,
            )
        )
    if dataset == "library":
        return update_library(
            LibraryUpdateOptions(
                dry_run=dry_run,
                limit=args.limit,
            )
        )
    if dataset == "metrics":
        return update_metrics(
            MetricsUpdateOptions(
                dry_run=dry_run,
                limit=args.limit,
            )
        )
    if dataset == "parks":
        return update_parks(
            ParksUpdateOptions(
                dry_run=dry_run,
                force=args.force,
                limit=args.limit,
            )
        )
    if dataset == "populations":
        return update_populations(
            PopulationsUpdateOptions(
                dry_run=dry_run,
                limit=args.limit,
                start_ym=args.start_ym,
                end_ym=args.end_ym,
            )
        )
    if dataset == "rent_deals":
        return update_rent_deals(
            RentDealsUpdateOptions(
                dry_run=dry_run,
                force=args.force,
                limit=args.limit,
                start_ym=args.start_ym,
                end_ym=args.end_ym,
            )
        )
    if dataset == "stores":
        return update_stores(
            StoresUpdateOptions(
                dry_run=dry_run,
                force=args.force,
                limit=args.limit,
            )
        )
    if dataset == "subway":
        return update_subway(
            SubwayUpdateOptions(
                dry_run=dry_run,
                force=args.force,
                limit=args.limit,
            )
        )
    if dataset == "univ":
        return update_univ(
            UnivUpdateOptions(
                dry_run=dry_run,
                force=args.force,
                limit=args.limit,
            )
        )
    raise ValueError(f"Unknown dataset: {dataset}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update public-data datasets.")
    parser.add_argument(
        "--dataset",
        default="all",
        choices=["all", *DATASET_ORDER],
        help="Dataset to update.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write DB/state changes.")
    parser.add_argument("--write", action="store_true", help="Write DB/state changes.")
    parser.add_argument("--skip-stops", action="store_true", help="Skip bus_stop update.")
    parser.add_argument("--skip-congestion", action="store_true", help="Skip bus_congestion update.")
    parser.add_argument("--start-date", help="Override bus_congestion start date: YYYY-MM-DD.")
    parser.add_argument("--end-date", help="Override bus_congestion end date: YYYY-MM-DD.")
    parser.add_argument("--start-ym", help="Override monthly dataset start month: YYYYMM.")
    parser.add_argument("--end-ym", help="Override monthly dataset end month: YYYYMM.")
    parser.add_argument("--limit", type=int, help="Stop after roughly this many checked rows.")
    parser.add_argument("--force", action="store_true", help="Force file-based snapshot reload.")
    args = parser.parse_args()

    if args.dry_run and args.write:
        raise SystemExit("--dry-run and --write cannot be used together")

    dry_run = not args.write
    if args.dry_run:
        dry_run = True

    if args.dataset == "all":
        result = {
            "dry_run": dry_run,
            "order": DATASET_ORDER,
            "datasets": {},
        }
        for dataset in DATASET_ORDER:
            try:
                dataset_result = _run_dataset(dataset, args, dry_run=dry_run)
            except RateLimitedError as exc:
                dataset_result = {
                    "dataset": dataset,
                    "dry_run": dry_run,
                    "status": "rate_limited",
                    "completed": False,
                    "error": str(exc),
                }
                result["datasets"][dataset] = dataset_result
                result["status"] = "rate_limited"
                result["completed"] = False
                result["stopped_at"] = dataset
                break
            except Exception as exc:
                dataset_result = {
                    "dataset": dataset,
                    "dry_run": dry_run,
                    "status": "failed",
                    "completed": False,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
                result["datasets"][dataset] = dataset_result
                result["status"] = "failed"
                result["completed"] = False
                result["stopped_at"] = dataset
                break
            result["datasets"][dataset] = dataset_result
            if _contains_unsuccessful(dataset_result):
                result["status"] = _unsuccessful_status(dataset_result)
                result["completed"] = False
                result["stopped_at"] = dataset
                break
        else:
            result["status"] = "success"
            result["completed"] = True
    else:
        result = _run_dataset(args.dataset, args, dry_run=dry_run)

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result.get("status") in {"rate_limited", "partial"}:
        return 2
    if _contains_unsuccessful(result):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
