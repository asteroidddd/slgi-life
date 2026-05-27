"""Run service-data updaters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _django import setup  # noqa: E402

setup()

from apps.service.amenities.updater import rebuild_amenities  # noqa: E402
from apps.service.scoring.updater import recompute_current_scores  # noqa: E402


TARGET_ORDER = ("amenity", "current")
UNSUCCESSFUL_STATUSES = {"rate_limited", "partial", "failed", "error"}


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


def _run_target(target: str, *, dry_run: bool) -> dict:
    if target == "amenity":
        return rebuild_amenities(dry_run=dry_run)
    if target == "current":
        return recompute_current_scores(dry_run=dry_run)
    raise ValueError(f"Unknown target: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update derived service datasets.")
    parser.add_argument(
        "--target",
        default="all",
        choices=["all", *TARGET_ORDER],
        help="Service dataset to update.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write DB changes.")
    parser.add_argument("--write", action="store_true", help="Write DB changes.")
    args = parser.parse_args()

    if args.dry_run and args.write:
        raise SystemExit("--dry-run and --write cannot be used together")

    dry_run = not args.write
    if args.dry_run:
        dry_run = True

    if args.target == "all":
        result = {
            "dry_run": dry_run,
            "order": TARGET_ORDER,
            "targets": {},
        }
        for target in TARGET_ORDER:
            try:
                target_result = _run_target(target, dry_run=dry_run)
            except Exception as exc:
                target_result = {
                    "target": target,
                    "dry_run": dry_run,
                    "status": "failed",
                    "completed": False,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
                result["targets"][target] = target_result
                result["status"] = "failed"
                result["completed"] = False
                result["stopped_at"] = target
                break
            result["targets"][target] = target_result
            if _contains_unsuccessful(target_result):
                result["status"] = "partial"
                result["completed"] = False
                result["stopped_at"] = target
                break
        else:
            result["status"] = "success"
            result["completed"] = True
    else:
        result = _run_target(args.target, dry_run=dry_run)

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result.get("status") == "partial":
        return 2
    if _contains_unsuccessful(result):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
