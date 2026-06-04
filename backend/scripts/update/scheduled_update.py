"""Scheduled EC2 updater with per-updater JSON state.

Default mode is plan-only. Use --write from systemd.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _django import setup  # noqa: E402

setup()

from apps.ai_agent.byok.services import purge_stale_user_keys  # noqa: E402
from scripts.update.bus_congestion_fast import (  # noqa: E402
    FastBusCongestionOptions,
    update_bus_congestion_fast,
)
from scripts.update.update_dashboard_data import _run_target as run_dashboard_target  # noqa: E402
from scripts.update.update_public_data import _run_dataset as run_public_dataset  # noqa: E402
from scripts.update.update_service_data import _run_target as run_service_target  # noqa: E402


KST = ZoneInfo("Asia/Seoul")
STATE_DIR = Path(__file__).resolve().parent / ".state"
RUN_STATE_PATH = STATE_DIR / "scheduled_update_latest.json"
PERSISTENT_FAILURES_PATH = STATE_DIR / "persistent_failures.md"
LOCK_PATH = STATE_DIR / "scheduled_update.lock"
DEFAULT_MAX_HOURS = 6.0
FAILED_STATUSES = {"failed", "partial", "rate_limited", "timeout"}
NON_RETRY_REASONS = {"deadline_reached"}


@dataclass(frozen=True)
class Task:
    task_id: str
    group: str
    order: str
    schedule: str
    runner: Callable[[argparse.Namespace, bool], dict[str, Any]]
    deps: tuple[str, ...] = ()
    file_paths: tuple[str, ...] = ()
    monthly_day: int | None = None
    weekly_day: int | None = None
    run_on_dependency_change: bool = False
    description: str = ""
    heavy: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def local_now() -> datetime:
    return datetime.now(KST).replace(microsecond=0)


def local_date_text(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def local_month_text(now: datetime) -> str:
    return now.strftime("%Y-%m")


def local_week_text(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"status": "corrupt", "corrupt_detected_at": utc_now()}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    os.replace(tmp, path)


def state_path(task_id: str) -> Path:
    return STATE_DIR / f"{task_id}.json"


def task_state(task_id: str) -> dict[str, Any]:
    return read_json(state_path(task_id))


def stable_hash(paths: tuple[str, ...]) -> str | None:
    if not paths:
        return None
    import hashlib

    digest = hashlib.sha256()
    base = Path(__file__).resolve().parents[2]
    for item in paths:
        path = (base / item).resolve()
        digest.update(str(path).encode("utf-8"))
        digest.update(b"\0")
        if not path.exists():
            digest.update(b"missing")
            digest.update(b"\0")
            continue
        if path.is_file():
            digest.update(str(path.stat().st_size).encode("ascii"))
            digest.update(str(int(path.stat().st_mtime)).encode("ascii"))
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def result_has_change(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("skipped_write") is True:
            return False
        if value.get("status") == "skipped":
            return False
        for key in (
            "created",
            "updated",
            "inserted",
            "deleted_missing",
            "deleted_existing",
            "imported",
            "deleted_old",
            "upserted",
            "stale_key_count",
            "deleted_key_count",
        ):
            item = value.get(key)
            if isinstance(item, bool):
                continue
            if isinstance(item, int) and item > 0:
                return True
            if isinstance(item, dict) and any(isinstance(v, int) and v > 0 for v in item.values()):
                return True
        return any(result_has_change(item) for item in value.values())
    if isinstance(value, list):
        return any(result_has_change(item) for item in value)
    return False


def contains_reason(value: Any, reasons: set[str]) -> bool:
    if isinstance(value, dict):
        if value.get("reason") in reasons:
            return True
        return any(contains_reason(item, reasons) for item in value.values())
    if isinstance(value, list):
        return any(contains_reason(item, reasons) for item in value)
    return False


def task_success_should_signal_change(task: Task, due_reason: str, result: dict[str, Any]) -> bool:
    if result_has_change(result):
        return True
    if task.extra.get("signal_on_success"):
        return True
    if task.schedule == "file_change" and due_reason in {"no_previous_success", "source_hash_changed_or_missing", "force"}:
        return True
    return False


def contains_unsuccessful(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("error"):
            return True
        if value.get("completed") is False:
            return True
        if value.get("status") in FAILED_STATUSES:
            return True
        return any(contains_unsuccessful(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_unsuccessful(item) for item in value)
    return False


def unsuccessful_status(value: Any) -> str:
    if isinstance(value, dict):
        if value.get("status") == "rate_limited":
            return "rate_limited"
        for item in value.values():
            found = unsuccessful_status(item)
            if found == "rate_limited":
                return found
    if isinstance(value, list):
        for item in value:
            found = unsuccessful_status(item)
            if found == "rate_limited":
                return found
    return "partial"


def public_args(args: argparse.Namespace, **overrides: Any) -> SimpleNamespace:
    values = {
        "force": args.force,
        "limit": args.limit,
        "skip_stops": False,
        "skip_congestion": False,
        "start_date": None,
        "end_date": None,
        "start_ym": None,
        "end_ym": None,
        "skip_geocode": False,
        "skip_delete_missing": False,
        "include_hira_specialties": False,
        "deadline_monotonic": args.deadline_monotonic,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def run_public(dataset: str, **overrides: Any) -> Callable[[argparse.Namespace, bool], dict[str, Any]]:
    def runner(args: argparse.Namespace, dry_run: bool) -> dict[str, Any]:
        return run_public_dataset(dataset, public_args(args, **overrides), dry_run=dry_run)

    return runner


def run_service(target: str) -> Callable[[argparse.Namespace, bool], dict[str, Any]]:
    def runner(_args: argparse.Namespace, dry_run: bool) -> dict[str, Any]:
        return run_service_target(target, dry_run=dry_run)

    return runner


def run_dashboard(_args: argparse.Namespace, dry_run: bool) -> dict[str, Any]:
    return run_dashboard_target("dashboard_cache", dry_run=dry_run, strict=False)


def run_bus_congestion(args: argparse.Namespace, dry_run: bool) -> dict[str, Any]:
    return update_bus_congestion_fast(
        FastBusCongestionOptions(
            dry_run=dry_run,
            days=args.bus_days,
            workers=args.bus_workers,
            rps=args.bus_rps,
            max_api_calls=args.bus_max_api_calls,
            deadline_monotonic=args.deadline_monotonic,
            anchor_ymd=args.bus_anchor_ymd,
        )
    )


def run_ai_stale_keys(_args: argparse.Namespace, dry_run: bool) -> dict[str, Any]:
    stale_count = purge_stale_user_keys(dry_run=dry_run)
    return {
        "target": "ai_stale_keys",
        "dry_run": dry_run,
        "status": "success",
        "completed": True,
        "stale_key_count": stale_count,
        "deleted_key_count": 0 if dry_run else stale_count,
    }


TASKS: tuple[Task, ...] = (
    Task(
        "regions",
        "public_data",
        "P01",
        "file_change",
        run_public("regions"),
        file_paths=(
            "data/gu_code.csv",
            "data/ldong_code.csv",
            "data/adong_code.csv",
            "data/gu_boundaries.geojson",
            "data/ldong_boundaries.geojson",
            "data/adong_boundaries.geojson",
        ),
    ),
    Task("metrics", "public_data", "P02", "monthly", run_public("metrics"), deps=("regions",), monthly_day=1, extra={"signal_on_success": True}),
    Task(
        "populations",
        "public_data",
        "P03",
        "monthly",
        run_public("populations"),
        deps=("regions",),
        monthly_day=1,
        heavy=True,
        extra={"allow_partial": True},
    ),
    Task("rent_deals", "public_data", "P04", "daily", run_public("rent_deals"), deps=("regions",), heavy=True, extra={"signal_on_success": True}),
    Task("univ", "public_data", "P05", "file_change", run_public("univ"), deps=("regions",), file_paths=("data/university_boundaries.geojson",)),
    Task("bus_stop", "public_data", "P06A", "daily", run_public("bus", skip_congestion=True), deps=("regions",)),
    Task("bus_congestion", "public_data", "P06B", "daily", run_bus_congestion, deps=("bus_stop",), heavy=True),
    Task("subway", "public_data", "P07", "daily", run_public("subway"), deps=("regions",), extra={"signal_on_success": True}),
    Task(
        "stores",
        "public_data",
        "P08",
        "weekly",
        run_public("stores"),
        deps=("regions",),
        weekly_day=0,
        file_paths=("data/store_business_category.xlsx", "data/KSIC_10th.xlsx"),
        heavy=True,
        extra={"signal_on_success": True},
    ),
    Task("daiso", "public_data", "P09", "weekly", run_public("daiso"), deps=("stores",), weekly_day=0, extra={"signal_on_success": True}),
    Task(
        "medical",
        "public_data",
        "P10",
        "weekly",
        run_public("medical", include_hira_specialties=True),
        deps=("regions",),
        weekly_day=0,
        heavy=True,
        extra={"signal_on_success": True},
    ),
    Task("parks", "public_data", "P11", "file_change", run_public("parks"), deps=("regions",), file_paths=("data/park_boundaries.geojson",)),
    Task("library", "public_data", "P12", "weekly", run_public("library"), deps=("regions",), weekly_day=0, extra={"signal_on_success": True}),
    Task(
        "amenity",
        "service",
        "S01",
        "on_change",
        run_service("amenity"),
        deps=("stores", "daiso", "medical", "library", "subway", "bus_stop"),
        run_on_dependency_change=True,
    ),
    Task(
        "current_scores",
        "service",
        "S02",
        "on_change",
        run_service("current"),
        deps=("rent_deals", "amenity", "bus_stop", "subway", "metrics"),
        run_on_dependency_change=True,
    ),
    Task(
        "dashboard_cache",
        "dashboard",
        "D01",
        "on_change",
        run_dashboard,
        deps=(
            "current_scores",
            "rent_deals",
            "bus_congestion",
            "subway",
            "bus_stop",
        ),
        run_on_dependency_change=True,
    ),
    Task("ai_stale_keys", "maintenance", "M01", "daily", run_ai_stale_keys),
)


def dependency_changed(task: Task, run_results: dict[str, dict[str, Any]]) -> bool:
    return any(run_results.get(dep, {}).get("changed") for dep in task.deps)


def dependency_failed_without_previous_success(task: Task, run_results: dict[str, dict[str, Any]]) -> tuple[bool, str | None]:
    for dep in task.deps:
        current = run_results.get(dep, {})
        if current.get("status") in FAILED_STATUSES and not task_state(dep).get("last_success_at"):
            return True, dep
    return False, None


def should_run(task: Task, args: argparse.Namespace, now: datetime, run_results: dict[str, dict[str, Any]]) -> tuple[bool, str, str | None]:
    previous = task_state(task.task_id)
    source_hash = stable_hash(task.file_paths)
    last_status = previous.get("status")

    if args.force:
        return True, "force", source_hash
    if last_status in FAILED_STATUSES:
        return True, f"retry_previous_{last_status}", source_hash

    if task.schedule == "daily":
        if previous.get("last_success_local_date") == local_date_text(now):
            return False, "already_succeeded_today", source_hash
        return True, "daily_due", source_hash

    if task.schedule == "monthly":
        if task.monthly_day is None:
            return False, "monthly_day_not_configured", source_hash
        if now.day < task.monthly_day:
            return False, "before_monthly_day", source_hash
        if previous.get("last_success_local_month") == local_month_text(now):
            return False, "already_succeeded_this_month", source_hash
        return True, "monthly_due", source_hash

    if task.schedule == "weekly":
        if task.weekly_day is None:
            return False, "weekly_day_not_configured", source_hash
        if previous.get("last_success_local_week") == local_week_text(now):
            return False, "already_succeeded_this_week", source_hash
        if now.weekday() < task.weekly_day:
            return False, "before_weekly_day", source_hash
        return True, "weekly_due", source_hash

    if task.schedule == "file_change":
        if not previous.get("last_success_at"):
            return True, "no_previous_success", source_hash
        if source_hash and previous.get("source_hash") == source_hash:
            return False, "source_hash_unchanged", source_hash
        return True, "source_hash_changed_or_missing", source_hash

    if task.schedule == "on_change":
        if dependency_changed(task, run_results):
            return True, "dependency_changed", source_hash
        if not previous.get("last_success_at"):
            return True, "no_previous_success", source_hash
        return False, "dependencies_unchanged", source_hash

    return False, "unknown_schedule", source_hash


def save_task_result(
    task: Task,
    *,
    status: str,
    reason: str,
    source_hash: str | None,
    result: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
    changed: bool = False,
    attempts: int = 0,
    started_at: str | None = None,
) -> dict[str, Any]:
    now = local_now()
    previous = task_state(task.task_id)
    consecutive_failures = int(previous.get("consecutive_failures") or 0)
    payload = {
        "task_id": task.task_id,
        "group": task.group,
        "order": task.order,
        "schedule": task.schedule,
        "status": status,
        "reason": reason,
        "changed": changed,
        "attempts": attempts,
        "last_run_at": utc_now(),
        "last_run_local_date": local_date_text(now),
        "source_hash": source_hash,
        "target_tables": task.extra.get("target_tables"),
        "updated_at": utc_now(),
    }
    if started_at:
        payload["started_at"] = started_at
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error

    if status == "success":
        payload["last_success_at"] = utc_now()
        payload["last_success_local_date"] = local_date_text(now)
        payload["last_success_local_month"] = local_month_text(now)
        payload["last_success_local_week"] = local_week_text(now)
        payload["consecutive_failures"] = 0
    elif status in FAILED_STATUSES:
        payload["last_failed_at"] = utc_now()
        payload["consecutive_failures"] = consecutive_failures + 1
        for key in ("last_success_at", "last_success_local_date", "last_success_local_month", "last_success_local_week"):
            if previous.get(key):
                payload[key] = previous[key]
    else:
        payload["consecutive_failures"] = consecutive_failures
        for key in ("last_success_at", "last_success_local_date", "last_success_local_month", "last_success_local_week"):
            if previous.get(key):
                payload[key] = previous[key]

    write_json(state_path(task.task_id), payload)
    if payload.get("consecutive_failures", 0) >= 3 and status in FAILED_STATUSES:
        append_persistent_failure(task, payload)
    return payload


def append_persistent_failure(task: Task, payload: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    line = (
        f"- {utc_now()} `{task.task_id}` consecutive_failures={payload.get('consecutive_failures')} "
        f"status={payload.get('status')} reason={payload.get('reason')}\n"
    )
    if not PERSISTENT_FAILURES_PATH.exists():
        PERSISTENT_FAILURES_PATH.write_text("# Persistent Update Failures\n\n", encoding="utf-8")
    with PERSISTENT_FAILURES_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line)


def run_task(task: Task, args: argparse.Namespace, dry_run: bool, source_hash: str | None, due_reason: str) -> dict[str, Any]:
    started_at = utc_now()
    last_error: dict[str, Any] | None = None
    last_result: dict[str, Any] | None = None
    last_status = "failed"
    for attempt in range(1, args.retry_attempts + 1):
        try:
            result = task.runner(args, dry_run)
            status = "success"
            if contains_unsuccessful(result):
                status = unsuccessful_status(result)
            last_result = result
            last_status = status
            if status == "partial" and task.extra.get("allow_partial"):
                result = {
                    **result,
                    "scheduler_warning_status": "partial",
                    "scheduler_warning_reason": "allowed_partial_result",
                }
                return save_task_result(
                    task,
                    status="success",
                    reason="executed_with_partial_warning",
                    source_hash=source_hash,
                    result=result,
                    changed=task_success_should_signal_change(task, due_reason, result),
                    attempts=attempt,
                    started_at=started_at,
                )
            if status == "success":
                return save_task_result(
                    task,
                    status=status,
                    reason="executed",
                    source_hash=source_hash,
                    result=result,
                    changed=task_success_should_signal_change(task, due_reason, result),
                    attempts=attempt,
                    started_at=started_at,
                )
            if contains_reason(result, NON_RETRY_REASONS):
                return save_task_result(
                    task,
                    status=status,
                    reason="non_retryable_unsuccessful_result",
                    source_hash=source_hash,
                    result=result,
                    changed=False,
                    attempts=attempt,
                    started_at=started_at,
                )
            if attempt < args.retry_attempts:
                time.sleep(args.retry_wait_seconds)
        except Exception as exc:
            last_error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            if attempt < args.retry_attempts:
                time.sleep(args.retry_wait_seconds)

    if last_result is not None:
        return save_task_result(
            task,
            status=last_status,
            reason="retry_exhausted_unsuccessful_result",
            source_hash=source_hash,
            result=last_result,
            changed=False,
            attempts=args.retry_attempts,
            started_at=started_at,
        )
    return save_task_result(
        task,
        status="failed",
        reason="retry_exhausted_exception",
        source_hash=source_hash,
        error=last_error,
        changed=False,
        attempts=args.retry_attempts,
        started_at=started_at,
    )


class FileLock:
    def __init__(self, path: Path, stale_after_seconds: int) -> None:
        self.path = path
        self.stale_after_seconds = stale_after_seconds
        self.fd: int | None = None

    def __enter__(self) -> "FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            if self._clear_stale():
                self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            else:
                raise RuntimeError(f"scheduled update lock exists: {self.path}") from exc
        os.write(self.fd, json.dumps({"pid": os.getpid(), "created_at": utc_now()}).encode("utf-8"))
        return self

    def _clear_stale(self) -> bool:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            created = datetime.fromisoformat(str(payload.get("created_at")).replace("Z", "+00:00"))
        except Exception:
            return False
        if (datetime.now(timezone.utc) - created).total_seconds() <= self.stale_after_seconds:
            return False
        self.path.unlink()
        return True

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        if self.fd is not None:
            os.close(self.fd)
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def run(args: argparse.Namespace) -> dict[str, Any]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    now = local_now()
    dry_run = not args.write
    if args.plan_only:
        dry_run = True

    if args.not_before_local_date and local_date_text(now) < args.not_before_local_date:
        result = {
            "status": "success",
            "completed": True,
            "dry_run": dry_run,
            "plan_only": bool(args.plan_only),
            "skipped": True,
            "reason": "before_not_before_local_date",
            "not_before_local_date": args.not_before_local_date,
            "started_at": utc_now(),
            "started_local": now.isoformat(),
            "finished_at": utc_now(),
            "finished_local": local_now().isoformat(),
            "tasks": [],
        }
        write_json(RUN_STATE_PATH, result)
        return result

    started = time.monotonic()
    args.deadline_monotonic = started + args.max_hours * 3600
    run_results: dict[str, dict[str, Any]] = {}
    run_payload: dict[str, Any] = {
        "status": "running",
        "completed": False,
        "dry_run": dry_run,
        "plan_only": bool(args.plan_only),
        "started_at": utc_now(),
        "started_local": now.isoformat(),
        "max_hours": args.max_hours,
        "tasks": [],
    }
    write_json(RUN_STATE_PATH, run_payload)

    for task in TASKS:
        if time.monotonic() >= args.deadline_monotonic:
            state = save_task_result(
                task,
                status="timeout",
                reason="max_hours_exceeded_before_step",
                source_hash=stable_hash(task.file_paths),
                changed=False,
                attempts=0,
            )
            run_results[task.task_id] = state
            run_payload["tasks"].append(state)
            break

        blocked, dep = dependency_failed_without_previous_success(task, run_results)
        if blocked:
            source_hash = stable_hash(task.file_paths)
            state = save_task_result(
                task,
                status="skipped",
                reason=f"dependency_failed_without_previous_success:{dep}",
                source_hash=source_hash,
                changed=False,
            )
            run_results[task.task_id] = state
            run_payload["tasks"].append(state)
            continue

        due, reason, source_hash = should_run(task, args, now, run_results)
        if not due:
            state = save_task_result(task, status="skipped", reason=reason, source_hash=source_hash, changed=False)
        elif args.plan_only:
            state = save_task_result(task, status="planned", reason=reason, source_hash=source_hash, changed=False)
        else:
            state = run_task(task, args, dry_run=dry_run, source_hash=source_hash, due_reason=reason)

        run_results[task.task_id] = state
        run_payload["tasks"].append(state)
        write_json(RUN_STATE_PATH, run_payload)

    failed = [item for item in run_payload["tasks"] if item.get("status") in FAILED_STATUSES]
    run_payload["status"] = "partial" if failed else "success"
    run_payload["completed"] = not failed
    run_payload["finished_at"] = utc_now()
    run_payload["finished_local"] = local_now().isoformat()
    run_payload["failed_tasks"] = [item.get("task_id") for item in failed]
    write_json(RUN_STATE_PATH, run_payload)
    return run_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run scheduled capston data updates.")
    parser.add_argument("--write", action="store_true", help="Write DB/state changes.")
    parser.add_argument("--plan-only", action="store_true", help="Only evaluate schedule, do not call updaters.")
    parser.add_argument("--force", action="store_true", help="Force all tasks due.")
    parser.add_argument("--limit", type=int, default=None, help="Debug limit passed to supported updaters.")
    parser.add_argument("--max-hours", type=float, default=DEFAULT_MAX_HOURS)
    parser.add_argument("--retry-attempts", type=int, default=5)
    parser.add_argument("--retry-wait-seconds", type=float, default=300.0)
    parser.add_argument("--bus-days", type=int, default=14)
    parser.add_argument("--bus-workers", type=int, default=8)
    parser.add_argument("--bus-rps", type=float, default=3.0)
    parser.add_argument("--bus-max-api-calls", type=int, default=90000)
    parser.add_argument("--bus-anchor-ymd", default=None)
    parser.add_argument("--not-before-local-date", default=None, help="YYYY-MM-DD KST guard.")
    args = parser.parse_args()

    if args.max_hours <= 0:
        raise SystemExit("--max-hours must be positive")
    if args.retry_attempts <= 0:
        raise SystemExit("--retry-attempts must be positive")
    if args.retry_wait_seconds < 0:
        raise SystemExit("--retry-wait-seconds must be non-negative")

    try:
        with FileLock(LOCK_PATH, stale_after_seconds=int(args.max_hours * 3600) + 900):
            result = run(args)
    except Exception as exc:
        result = {
            "status": "failed",
            "completed": False,
            "error": {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()},
            "finished_at": utc_now(),
        }
        write_json(RUN_STATE_PATH, result)

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if result.get("status") == "success":
        return 0
    if result.get("status") == "partial":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
