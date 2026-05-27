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
LOCK_FILE = STATE_DIR / "update_all.lock"
DEFAULT_MAX_HOURS = 6.0
PUBLIC_ORDER = (
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
SERVICE_ORDER = ("amenity", "current")

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


def _run_flow(args: argparse.Namespace) -> dict[str, Any]:
    from _django import setup  # noqa: WPS433

    setup()

    from apps.public_data.exceptions import RateLimitedError  # noqa: WPS433
    from scripts.update.update_public_data import (  # noqa: WPS433
        _contains_rate_limited,
        _contains_unsuccessful,
        _run_dataset,
    )
    from scripts.update.update_service_data import _run_target  # noqa: WPS433

    dry_run = not args.write
    if args.dry_run:
        dry_run = True

    max_seconds = int(args.max_hours * 3600)
    started_monotonic = time.monotonic()
    result: dict[str, Any] = {
        "status": "running",
        "completed": False,
        "dry_run": dry_run,
        "started_at": _utc_now_iso(),
        "max_seconds": max_seconds,
        "public_order": PUBLIC_ORDER,
        "service_order": SERVICE_ORDER,
        "steps": [],
    }
    public_args = _public_args(args)

    def stop_with(status: str, stopped_at: str, reason: str) -> dict[str, Any]:
        result["status"] = status
        result["completed"] = False
        result["stopped_at"] = stopped_at
        result["reason"] = reason
        return result

    for dataset in PUBLIC_ORDER:
        step_name = f"public.{dataset}"
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
        if STOP_REQUESTED:
            return stop_with("interrupted", step_name, "stop_signal")
        if _time_exceeded(started_monotonic, max_seconds):
            return stop_with("timeout", step_name, "max_hours_exceeded_before_step")

        step_started = _utc_now_iso()
        try:
            target_result = _run_target(target, dry_run=dry_run)
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
