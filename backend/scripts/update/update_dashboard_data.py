"""Run dashboard-data updaters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _django import setup  # noqa: E402

setup()

from apps.dashboard.cache.bulk import build_dashboard_payloads  # noqa: E402
from apps.dashboard.cache.updater import update_all as rebuild_dashboard_cache  # noqa: E402


TARGET_ORDER = ("dashboard_cache",)
TARGET_ALIASES = {"region_intro": "dashboard_cache"}
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


def _normalize_target(target: str) -> str:
    return TARGET_ALIASES.get(target, target)


def _dry_run_dashboard_cache() -> dict:
    counts = {
        region_type: len(build_dashboard_payloads(region_type))
        for region_type in ("adong", "ldong")
    }
    return {
        "target": "dashboard_cache",
        "dry_run": True,
        "status": "success",
        "completed": True,
        "rows": counts,
    }


def _write_dashboard_cache() -> dict:
    results = rebuild_dashboard_cache(region_type="all")
    failed = [item for item in results if not item.ok]
    rows = {
        "adong": sum(1 for item in results if item.region_type == "adong" and item.ok),
        "ldong": sum(1 for item in results if item.region_type == "ldong" and item.ok),
    }
    return {
        "target": "dashboard_cache",
        "dry_run": False,
        "status": "failed" if failed else "success",
        "completed": not failed,
        "rows": rows,
        "failed": [
            {
                "region_type": item.region_type,
                "code": item.code,
                "slug": item.slug,
                "error": item.error,
            }
            for item in failed[:20]
        ],
    }


def _run_target(target: str, *, dry_run: bool, strict: bool = False) -> dict:
    target = _normalize_target(target)
    if target == "dashboard_cache":
        result = _dry_run_dashboard_cache() if dry_run else _write_dashboard_cache()
        result["strict"] = strict
        return result
    raise ValueError(f"Unknown target: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update dashboard datasets.")
    parser.add_argument(
        "--target",
        default="all",
        choices=["all", *TARGET_ORDER, *TARGET_ALIASES],
        help="Dashboard dataset to update.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write DB changes.")
    parser.add_argument("--write", action="store_true", help="Write DB changes.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on unmatched source rows instead of skipping them.",
    )
    args = parser.parse_args()

    if args.dry_run and args.write:
        raise SystemExit("--dry-run and --write cannot be used together")

    dry_run = not args.write
    if args.dry_run:
        dry_run = True

    if args.target == "all":
        result = {
            "dry_run": dry_run,
            "strict": args.strict,
            "order": TARGET_ORDER,
            "targets": {},
        }
        for target in TARGET_ORDER:
            try:
                target_result = _run_target(target, dry_run=dry_run, strict=args.strict)
            except Exception as exc:
                target_result = {
                    "target": target,
                    "dry_run": dry_run,
                    "strict": args.strict,
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
        result = _run_target(args.target, dry_run=dry_run, strict=args.strict)

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result.get("status") == "partial":
        return 2
    if _contains_unsuccessful(result):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
