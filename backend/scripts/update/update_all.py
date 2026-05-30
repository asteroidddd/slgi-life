"""Run the full data update flow."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = BACKEND_ROOT / "apps" / "public_data" / ".state"
STATE_FILE = STATE_DIR / "update_all_state.json"
PUBLIC_DATA_STATE_FILE = STATE_DIR / "public_data_state.json"
LOCK_FILE = STATE_DIR / "update_all.lock"
DEFAULT_MAX_HOURS = 23.0
RESUMABLE_STATUSES = {"rate_limited", "partial", "timeout", "interrupted", "failed"}
PUBLIC_ORDER = (
    "regions",
    "metrics",
    "populations",
    "rent_deals",
    "univ",
    "bus",
    "subway",
    "stores",
    "medical",
    "parks",
    "library",
)
SERVICE_ORDER = ("amenity", "rent_deal_cache", "rent_deal_summary_cache", "current")
DASHBOARD_ORDER = ("dashboard_cache",)
MAINTENANCE_ORDER = ("ai_stale_keys",)

RESET_MANAGED_TABLES = (
    "django_admin_log",
    "django_session",
    "users_groups",
    "users_user_permissions",
    "auth_group_permissions",
    "auth_group",
    "user_ai_context_preference",
    "user_ai_api_key",
    "user_favorite",
    "user_social_account",
    "user_profile",
    "users",
    "dashboard_adong_cache",
    "dashboard_ldong_cache",
    "current_adong",
    "current_gu",
    "current_ldong",
    "current_seoul",
    "amenity_adong",
    "amenity_ldong",
    "amenity",
    "rent_deal_grid_monthly_cache",
    "rent_deal_ldong_monthly_cache",
    "rent_deal_cache",
    "medical_facility_specialty",
    "medical_hira_mapping",
    "medical_holiday_care",
    "medical_emergency",
    "medical_facility_hours",
    "medical_facility",
    "library_hours",
    "library",
    "store",
    "ksci_category",
    "business_category",
    "nearest_subway_adong",
    "nearest_subway_ldong",
    "subway_congestion",
    "subway_station",
    "bus_congestion",
    "bus_stop",
    "park_adong",
    "park_ldong",
    "park",
    "univ_adong",
    "univ_ldong",
    "univ",
    "rent_deal",
    "rent_deal_ldong_adong_map",
    "adong_population",
    "ldong_population",
    "gu_metric",
    "seoul_metric",
    "metric",
    "adjacent_adong",
    "adjacent_ldong",
    "adjacent_gu",
    "adong",
    "ldong",
    "gu",
    "seoul",
)

STOP_REQUESTED = False


class LockError(RuntimeError):
    pass


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _save_state(result: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_FILE.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp_path, STATE_FILE)


def _load_state() -> dict[str, Any] | None:
    if not STATE_FILE.exists():
        return None
    try:
        with STATE_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _completed_resume_steps(
    previous: dict[str, Any] | None,
    *,
    dry_run: bool,
    force: bool,
    limit: int | None,
    reset_managed_data: bool,
) -> dict[str, dict[str, Any]]:
    if not previous or previous.get("status") not in RESUMABLE_STATUSES:
        return {}
    if bool(previous.get("dry_run")) != dry_run:
        return {}
    previous_args = previous.get("args")
    if isinstance(previous_args, dict) and (
        bool(previous_args.get("force")) != force
        or previous_args.get("limit") != limit
        or bool(previous_args.get("reset_managed_data")) != reset_managed_data
    ):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for step in previous.get("steps") or []:
        if not isinstance(step, dict):
            break
        name = step.get("name")
        if not isinstance(name, str) or step.get("status") != "success":
            break
        out[name] = step
    return out


def _resume_step_result(previous_step: dict[str, Any]) -> dict[str, Any]:
    step = dict(previous_step)
    step["resumed"] = True
    step["skip_reason"] = "previous_success"
    return step


def _handle_stop(_signum, _frame) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True


def _install_signal_handlers() -> None:
    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            signal.signal(sig, _handle_stop)


class FileLock:
    def __init__(self, path: Path, *, enabled: bool = True, stale_after_seconds: int) -> None:
        self.path = path
        self.enabled = enabled
        self.stale_after_seconds = stale_after_seconds
        self.fd: int | None = None

    def __enter__(self) -> "FileLock":
        if not self.enabled:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            if self._clear_stale_lock():
                self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            else:
                raise LockError(f"update lock already exists: {self.path}") from exc
        payload = {"created_at": _utc_now_iso(), "pid": os.getpid()}
        os.write(self.fd, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        return self

    def _clear_stale_lock(self) -> bool:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8") or "{}")
            raw_created_at = str(payload.get("created_at") or "")
            created_at = datetime.fromisoformat(raw_created_at.replace("Z", "+00:00"))
        except Exception:
            return False
        age = datetime.now(timezone.utc) - created_at
        if age.total_seconds() <= self.stale_after_seconds:
            return False
        self.path.unlink()
        return True

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        if self.enabled:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass


def _public_args(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        force=args.force,
        limit=args.limit,
        skip_stops=False,
        skip_congestion=False,
        start_date=None,
        end_date=None,
        start_ym=None,
        end_ym=None,
        include_hira_specialties=False,
        deadline_monotonic=getattr(args, "deadline_monotonic", None),
    )


def _step_result(
    *,
    name: str,
    kind: str,
    status: str,
    started_at: str,
    result: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "status": status,
        "started_at": started_at,
        "finished_at": _utc_now_iso(),
    }
    if result is not None:
        out["result"] = result
    if error is not None:
        out["error"] = error
    return out


def _time_exceeded(start_monotonic: float, max_seconds: float) -> bool:
    return time.monotonic() - start_monotonic >= max_seconds


def _reset_managed_data(*, dry_run: bool) -> dict[str, Any]:
    from django.db import connection, transaction  # noqa: WPS433

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = current_schema()
            """
        )
        existing = {row[0] for row in cursor.fetchall()}

    tables = [table for table in RESET_MANAGED_TABLES if table in existing]
    skipped_missing = [table for table in RESET_MANAGED_TABLES if table not in existing]
    result: dict[str, Any] = {
        "target": "managed_data_reset",
        "dry_run": dry_run,
        "status": "success",
        "completed": True,
        "tables": tables,
        "table_count": len(tables),
        "skipped_missing": skipped_missing,
        "public_data_state_removed": False,
    }
    if dry_run:
        return result

    quoted_tables = ", ".join(connection.ops.quote_name(table) for table in tables)
    with transaction.atomic():
        if quoted_tables:
            with connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE")

    try:
        PUBLIC_DATA_STATE_FILE.unlink()
        result["public_data_state_removed"] = True
    except FileNotFoundError:
        result["public_data_state_removed"] = False

    return result


def _run_flow(args: argparse.Namespace) -> dict[str, Any]:
    from _django import setup  # noqa: WPS433

    setup()

    from apps.public_data.exceptions import RateLimitedError  # noqa: WPS433
    from scripts.update.update_public_data import (  # noqa: WPS433
        _contains_rate_limited,
        _contains_unsuccessful,
        _run_dataset,
    )
    from scripts.update.update_dashboard_data import _run_target as _run_dashboard_target  # noqa: WPS433
    from scripts.update.update_service_data import _run_target as _run_service_target  # noqa: WPS433
    from apps.ai_agent.byok.services import purge_stale_user_keys  # noqa: WPS433

    dry_run = not args.write
    if args.dry_run:
        dry_run = True

    max_seconds = int(args.max_hours * 3600)
    started_monotonic = time.monotonic()
    args.deadline_monotonic = started_monotonic + max_seconds
    resume_steps = (
        {}
        if args.no_resume
        else _completed_resume_steps(
            _load_state(),
            dry_run=dry_run,
            force=bool(args.force),
            limit=args.limit,
            reset_managed_data=bool(args.reset_managed_data),
        )
    )
    result: dict[str, Any] = {
        "status": "running",
        "completed": False,
        "dry_run": dry_run,
        "started_at": _utc_now_iso(),
        "max_seconds": max_seconds,
        "resume_enabled": not args.no_resume,
        "resumed_steps": sorted(resume_steps),
        "args": {
            "dry_run": bool(args.dry_run),
            "write": bool(args.write),
            "force": bool(args.force),
            "limit": args.limit,
            "max_hours": args.max_hours,
            "no_resume": bool(args.no_resume),
            "reset_managed_data": bool(args.reset_managed_data),
        },
        "public_order": PUBLIC_ORDER,
        "service_order": SERVICE_ORDER,
        "dashboard_order": DASHBOARD_ORDER,
        "maintenance_order": MAINTENANCE_ORDER,
        "steps": [],
    }
    public_args = _public_args(args)

    def stop_with(status: str, stopped_at: str, reason: str) -> dict[str, Any]:
        result["status"] = status
        result["completed"] = False
        result["stopped_at"] = stopped_at
        result["reason"] = reason
        return result

    reset_step_name = "reset.managed_data"
    if args.reset_managed_data:
        if reset_step_name in resume_steps:
            result["steps"].append(_resume_step_result(resume_steps[reset_step_name]))
            _save_state(result)
        else:
            if STOP_REQUESTED:
                return stop_with("interrupted", reset_step_name, "stop_signal")
            if _time_exceeded(started_monotonic, max_seconds):
                return stop_with("timeout", reset_step_name, "max_hours_exceeded_before_step")
            step_started = _utc_now_iso()
            try:
                reset_result = _reset_managed_data(dry_run=dry_run)
            except Exception as exc:
                result["steps"].append(
                    _step_result(
                        name=reset_step_name,
                        kind="reset",
                        status="failed",
                        started_at=step_started,
                        error={
                            "type": type(exc).__name__,
                            "message": str(exc),
                            "traceback": traceback.format_exc(),
                        },
                    )
                )
                _save_state(result)
                return stop_with("failed", reset_step_name, "reset_failed")
            result["steps"].append(
                _step_result(
                    name=reset_step_name,
                    kind="reset",
                    status="success",
                    started_at=step_started,
                    result=reset_result,
                )
            )
            _save_state(result)

    for dataset in PUBLIC_ORDER:
        step_name = f"public.{dataset}"
        if step_name in resume_steps:
            result["steps"].append(_resume_step_result(resume_steps[step_name]))
            _save_state(result)
            continue
        if STOP_REQUESTED:
            return stop_with("interrupted", step_name, "stop_signal")
        if _time_exceeded(started_monotonic, max_seconds):
            return stop_with("timeout", step_name, "max_hours_exceeded_before_step")

        step_started = _utc_now_iso()
        try:
            dataset_result = _run_dataset(dataset, public_args, dry_run=dry_run)
        except RateLimitedError as exc:
            result["steps"].append(
                _step_result(
                    name=step_name,
                    kind="public",
                    status="rate_limited",
                    started_at=step_started,
                    error={"type": type(exc).__name__, "message": str(exc)},
                )
            )
            return stop_with("rate_limited", step_name, "api_rate_limited")
        except Exception as exc:
            result["steps"].append(
                _step_result(
                    name=step_name,
                    kind="public",
                    status="failed",
                    started_at=step_started,
                    error={
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                )
            )
            return stop_with("failed", step_name, "step_failed")

        if _contains_rate_limited(dataset_result):
            status = "rate_limited"
        elif _contains_unsuccessful(dataset_result):
            status = "partial"
        else:
            status = "success"
        result["steps"].append(
            _step_result(
                name=step_name,
                kind="public",
                status=status,
                started_at=step_started,
                result=dataset_result,
            )
        )
        _save_state(result)
        if status == "rate_limited":
            return stop_with("rate_limited", step_name, "api_rate_limited")
        if status == "partial":
            return stop_with("partial", step_name, "step_incomplete")

    for target in SERVICE_ORDER:
        step_name = f"service.{target}"
        if step_name in resume_steps:
            result["steps"].append(_resume_step_result(resume_steps[step_name]))
            _save_state(result)
            continue
        if STOP_REQUESTED:
            return stop_with("interrupted", step_name, "stop_signal")
        if _time_exceeded(started_monotonic, max_seconds):
            return stop_with("timeout", step_name, "max_hours_exceeded_before_step")

        step_started = _utc_now_iso()
        try:
            target_result = _run_service_target(target, dry_run=dry_run)
        except Exception as exc:
            result["steps"].append(
                _step_result(
                    name=step_name,
                    kind="service",
                    status="failed",
                    started_at=step_started,
                    error={
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                )
            )
            return stop_with("failed", step_name, "step_failed")

        status = "partial" if _contains_unsuccessful(target_result) else "success"
        result["steps"].append(
            _step_result(
                name=step_name,
                kind="service",
                status=status,
                started_at=step_started,
                result=target_result,
            )
        )
        _save_state(result)
        if status == "partial":
            return stop_with("partial", step_name, "step_incomplete")

    for target in DASHBOARD_ORDER:
        step_name = f"dashboard.{target}"
        if step_name in resume_steps:
            result["steps"].append(_resume_step_result(resume_steps[step_name]))
            _save_state(result)
            continue
        if STOP_REQUESTED:
            return stop_with("interrupted", step_name, "stop_signal")
        if _time_exceeded(started_monotonic, max_seconds):
            return stop_with("timeout", step_name, "max_hours_exceeded_before_step")

        step_started = _utc_now_iso()
        try:
            target_result = _run_dashboard_target(target, dry_run=dry_run, strict=False)
        except Exception as exc:
            result["steps"].append(
                _step_result(
                    name=step_name,
                    kind="dashboard",
                    status="failed",
                    started_at=step_started,
                    error={
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                )
            )
            return stop_with("failed", step_name, "step_failed")

        status = "partial" if _contains_unsuccessful(target_result) else "success"
        result["steps"].append(
            _step_result(
                name=step_name,
                kind="dashboard",
                status=status,
                started_at=step_started,
                result=target_result,
            )
        )
        _save_state(result)
        if status == "partial":
            return stop_with("partial", step_name, "step_incomplete")

    for target in MAINTENANCE_ORDER:
        step_name = f"maintenance.{target}"
        if step_name in resume_steps:
            result["steps"].append(_resume_step_result(resume_steps[step_name]))
            _save_state(result)
            continue
        if STOP_REQUESTED:
            return stop_with("interrupted", step_name, "stop_signal")
        if _time_exceeded(started_monotonic, max_seconds):
            return stop_with("timeout", step_name, "max_hours_exceeded_before_step")

        step_started = _utc_now_iso()
        try:
            if target == "ai_stale_keys":
                stale_count = purge_stale_user_keys(dry_run=dry_run)
                target_result = {
                    "target": target,
                    "dry_run": dry_run,
                    "stale_key_count": stale_count,
                    "deleted_key_count": 0 if dry_run else stale_count,
                    "completed": True,
                }
            else:
                raise ValueError(f"Unknown maintenance target: {target}")
        except Exception as exc:
            result["steps"].append(
                _step_result(
                    name=step_name,
                    kind="maintenance",
                    status="failed",
                    started_at=step_started,
                    error={
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                )
            )
            return stop_with("failed", step_name, "step_failed")

        result["steps"].append(
            _step_result(
                name=step_name,
                kind="maintenance",
                status="success",
                started_at=step_started,
                result=target_result,
            )
        )
        _save_state(result)

    result["status"] = "success"
    result["completed"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full public/service data update flow.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write DB changes.")
    parser.add_argument("--write", action="store_true", help="Write DB changes.")
    parser.add_argument("--max-hours", type=float, default=DEFAULT_MAX_HOURS)
    parser.add_argument("--limit", type=int, help="Pass a rough row limit to public updaters.")
    parser.add_argument("--force", action="store_true", help="Force file-based public snapshots.")
    parser.add_argument("--no-lock", action="store_true", help="Allow running without update lock.")
    parser.add_argument("--no-resume", action="store_true", help="Ignore prior incomplete update_all state.")
    parser.add_argument(
        "--reset-managed-data",
        action="store_true",
        help="Truncate managed app/user data before the full reload. Keeps Django/system metadata.",
    )
    args = parser.parse_args()

    if args.dry_run and args.write:
        raise SystemExit("--dry-run and --write cannot be used together")
    if args.max_hours <= 0:
        raise SystemExit("--max-hours must be positive")

    _install_signal_handlers()

    with FileLock(
        LOCK_FILE,
        enabled=not args.no_lock,
        stale_after_seconds=int(args.max_hours * 3600) + 600,
    ):
        try:
            result = _run_flow(args)
        except Exception as exc:
            result = {
                "status": "failed",
                "completed": False,
                "dry_run": not args.write or args.dry_run,
                "started_at": _utc_now_iso(),
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            }
        result["finished_at"] = _utc_now_iso()
        _save_state(result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] == "success":
        return 0
    if result["status"] in {"rate_limited", "partial", "timeout", "interrupted"}:
        return 2
    return 1


def locked_main(args: argparse.Namespace, exc: LockError) -> int:
    result = {
        "status": "locked",
        "completed": False,
        "dry_run": not args.write or args.dry_run,
        "started_at": _utc_now_iso(),
        "finished_at": _utc_now_iso(),
        "error": {"type": type(exc).__name__, "message": str(exc)},
    }
    _save_state(result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LockError as exc:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--write", action="store_true")
        known_args, _unknown = parser.parse_known_args()
        raise SystemExit(locked_main(known_args, exc))
