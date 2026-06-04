"""Fast EC2 bus_congestion loader used by scheduled_update.

Runs inside the backend container. Uses Django DB connection, not docker exec.
"""

from __future__ import annotations

import csv
import json
import math
import threading
import time as sleep_time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db import connection, transaction

from apps.public_data.api_keys import env_key_ring
from apps.public_data.bus.models import BusCongestion, BusStop
from apps.public_data.exceptions import RateLimitedError


BUS_URL = "https://apis.data.go.kr/1613000/RouteCongestionLevel/getRouteCongestionLevel"
STOP_MAP_PATH = Path(__file__).resolve().parents[2] / "data" / "bus_congestion_stop_map.csv"
PAGE_SIZE = 1000
RETENTION_DAYS = 14
DEFAULT_LOOKBACK_DAYS = 500
DISCOVERY_GUS = ("11680", "11500", "11710", "11440")
BUS_SERVICE_START_HOUR = 4
BUS_SERVICE_END_HOUR = 27
BUS_SERVICE_HOURS = tuple(range(BUS_SERVICE_START_HOUR, BUS_SERVICE_END_HOUR + 1))
STAGE_TABLE_NAME = "tmp_bus_congestion_accum"
PAGE_TASK_CHUNK_FACTOR = 3


@dataclass(frozen=True)
class FastBusCongestionOptions:
    dry_run: bool = True
    days: int = RETENTION_DAYS
    workers: int = 8
    rps: float = 3.0
    page_size: int = PAGE_SIZE
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    request_timeout_seconds: float = 40.0
    max_api_calls: int = 90000
    max_rate_retries: int = 20
    deadline_monotonic: float | None = None
    anchor_ymd: str | None = None


class RateLimiter:
    def __init__(self, rps: float) -> None:
        self.rps = rps
        self.next_request_at = 0.0
        self.cooldown_until = 0.0
        self.lock = threading.Lock()

    def wait(self) -> None:
        if self.rps <= 0:
            return
        interval = 1.0 / self.rps
        while True:
            now = sleep_time.monotonic()
            with self.lock:
                wait_seconds = max(self.cooldown_until - now, self.next_request_at - now)
                if wait_seconds <= 0:
                    self.next_request_at = now + interval
                    return
            sleep_time.sleep(min(wait_seconds, 1.0))

    def cooldown(self, seconds: float) -> None:
        with self.lock:
            self.cooldown_until = max(self.cooldown_until, sleep_time.monotonic() + seconds)


class ApiCounter:
    def __init__(self, max_calls: int) -> None:
        self.max_calls = max_calls
        self.value = 0
        self.lock = threading.Lock()

    def bump(self) -> int:
        with self.lock:
            self.value += 1
            current = self.value
        if current > self.max_calls:
            raise RateLimitedError(f"bus congestion max_api_calls reached: {self.max_calls}")
        return current


def _deadline_reached(options: FastBusCongestionOptions) -> bool:
    return options.deadline_monotonic is not None and sleep_time.monotonic() >= options.deadline_monotonic


def _gu_codes() -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT gu_code FROM gu ORDER BY gu_code")
        return [str(row[0]) for row in cursor.fetchall()]


def _existing_stop_ids() -> set[int]:
    return {int(value) for value in BusStop.objects.values_list("id", flat=True) if str(value).isdigit()}


def _load_stop_id_map() -> tuple[dict[int, int], dict[str, Any]]:
    """Map RouteCongestionLevel sttn_id to the current EC2 bus_stop.id."""

    bus_stop_by_number: dict[str, int] = {}
    direct_ids: dict[int, int] = {}
    for stop_id, stop_number in BusStop.objects.values_list("id", "stop_number"):
        stop_id_text = str(stop_id or "").strip()
        if stop_id_text.isdigit():
            direct_ids[int(stop_id_text)] = int(stop_id_text)
        number = str(stop_number or "").strip()
        if number and stop_id_text.isdigit():
            bus_stop_by_number[number] = int(stop_id_text)

    mapping: dict[int, int] = dict(direct_ids)
    file_rows = matched_rows = unmatched_rows = bad_rows = 0
    matched_stop_numbers: set[str] = set()
    if STOP_MAP_PATH.exists():
        with STOP_MAP_PATH.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                file_rows += 1
                sttn_id_text = str(row.get("sttn_id") or "").strip()
                stop_number = str(row.get("stop_number") or "").strip()
                if not sttn_id_text.isdigit() or not stop_number:
                    bad_rows += 1
                    continue
                bus_stop_id = bus_stop_by_number.get(stop_number)
                if bus_stop_id is None:
                    unmatched_rows += 1
                    continue
                mapping[int(sttn_id_text)] = bus_stop_id
                matched_rows += 1
                matched_stop_numbers.add(stop_number)

    return mapping, {
        "file": str(STOP_MAP_PATH),
        "file_exists": STOP_MAP_PATH.exists(),
        "file_rows": file_rows,
        "matched_rows": matched_rows,
        "unmatched_rows": unmatched_rows,
        "bad_rows": bad_rows,
        "matched_stop_numbers": len(matched_stop_numbers),
        "direct_id_count": len(direct_ids),
        "mapping_count": len(mapping),
    }


def _request_json(
    *,
    api_key: str,
    params: dict[str, str],
    options: FastBusCongestionOptions,
    limiter: RateLimiter,
    counter: ApiCounter,
) -> dict[str, Any]:
    rate_retries = 0
    transient_delays = (0.5, 1.0, 2.0, 5.0)
    transient_attempt = 0
    while True:
        if _deadline_reached(options):
            raise TimeoutError("deadline reached before bus congestion request")
        limiter.wait()
        counter.bump()
        url = f"{BUS_URL}?{urlencode({'serviceKey': api_key, **params}, safe='%')}"
        req = Request(url, headers={"User-Agent": "capston-bus-congestion-fast/1.0"})
        try:
            with urlopen(req, timeout=options.request_timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            upper = body.upper()
            if exc.code in {403, 429} or "LIMIT" in upper or "QUOTA" in upper or "초과" in body:
                rate_retries += 1
                if rate_retries > options.max_rate_retries:
                    raise RateLimitedError(f"bus congestion API rate limited: HTTP {exc.code}") from exc
                limiter.cooldown(min(300.0, 20.0 + rate_retries * 20.0))
                continue
            if exc.code >= 500 and transient_attempt < len(transient_delays):
                sleep_time.sleep(transient_delays[transient_attempt])
                transient_attempt += 1
                continue
            raise RuntimeError(f"bus congestion HTTP {exc.code}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            if transient_attempt < len(transient_delays):
                sleep_time.sleep(transient_delays[transient_attempt])
                transient_attempt += 1
                continue
            raise RuntimeError(f"bus congestion request failed: {type(exc).__name__}") from exc


def _parse_payload(payload: dict[str, Any]) -> tuple[int, list[dict[str, Any]], str]:
    if "Error" in payload:
        error = payload.get("Error") or {}
        code = str(error.get("code") or "")
        message = str(error.get("message") or "")
        upper = message.upper()
        if code == "50" or "NO_DATA" in upper:
            return 0, [], message or "NO_DATA"
        if code in {"22", "30", "31", "429"} or "LIMIT" in upper or "QUOTA" in upper or "초과" in message:
            raise RateLimitedError(f"bus congestion API rate limited: {code} {message}")
        raise RuntimeError(f"bus congestion API error: {code} {message}")

    response = payload.get("response") or payload.get("Response") or {}
    header = response.get("header") or {}
    body = response.get("body") or {}
    code = str(header.get("resultCode") or "")
    message = str(header.get("resultMsg") or "")
    upper = message.upper()
    if code and code not in {"00", "0", "200", "SUCCESS", "NORMAL SERVICE."}:
        if code in {"22", "429"} or "LIMIT" in upper or "QUOTA" in upper or "초과" in message:
            raise RateLimitedError(f"bus congestion API rate limited: {code} {message}")
        if "NO_DATA" in upper:
            return 0, [], message
        raise RuntimeError(f"bus congestion API result: {code} {message}")

    total = int(body.get("totalCount") or 0)
    items = body.get("items") or {}
    rows = items.get("item") if isinstance(items, dict) else []
    if rows is None:
        parsed: list[dict[str, Any]] = []
    elif isinstance(rows, list):
        parsed = rows
    else:
        parsed = [rows]
    return total, parsed, message or "ok"


def _fetch_page(
    *,
    api_key: str,
    ymd: str,
    gu_code: str,
    page: int,
    options: FastBusCongestionOptions,
    limiter: RateLimiter,
    counter: ApiCounter,
) -> tuple[int, list[dict[str, Any]], str]:
    payload = _request_json(
        api_key=api_key,
        params={
            "pageNo": str(page),
            "numOfRows": str(options.page_size),
            "ctpv_cd": "11",
            "sgg_cd": gu_code,
            "opr_ymd": ymd,
            "dataType": "JSON",
        },
        options=options,
        limiter=limiter,
        counter=counter,
    )
    return _parse_payload(payload)


def _probe_date(api_key: str, ymd: str, options: FastBusCongestionOptions, limiter: RateLimiter, counter: ApiCounter) -> bool:
    for gu_code in DISCOVERY_GUS:
        total, _rows, _status = _fetch_page(
            api_key=api_key,
            ymd=ymd,
            gu_code=gu_code,
            page=1,
            options=FastBusCongestionOptions(
                dry_run=options.dry_run,
                days=options.days,
                workers=options.workers,
                rps=options.rps,
                page_size=1,
                lookback_days=options.lookback_days,
                request_timeout_seconds=options.request_timeout_seconds,
                max_api_calls=options.max_api_calls,
                max_rate_retries=options.max_rate_retries,
                deadline_monotonic=options.deadline_monotonic,
                anchor_ymd=options.anchor_ymd,
            ),
            limiter=limiter,
            counter=counter,
        )
        if total > 0:
            return True
    return False


def _latest_available_date(
    api_key: str,
    options: FastBusCongestionOptions,
    limiter: RateLimiter,
    counter: ApiCounter,
) -> date:
    if options.anchor_ymd:
        return datetime.strptime(options.anchor_ymd, "%Y%m%d").date()

    today = date.today()
    high = today - timedelta(days=1)
    if _probe_date(api_key, high.strftime("%Y%m%d"), options, limiter, counter):
        return high

    lower: date | None = None
    floor = today - timedelta(days=options.lookback_days)
    cursor = high
    while cursor >= floor:
        if _probe_date(api_key, cursor.strftime("%Y%m%d"), options, limiter, counter):
            lower = cursor
            break
        cursor -= timedelta(days=7)
    if lower is None:
        raise RuntimeError(f"no bus congestion data found in lookback_days={options.lookback_days}")

    latest = lower
    no_data_streak = 0
    cursor = lower + timedelta(days=1)
    while cursor <= high and no_data_streak < 14:
        if _probe_date(api_key, cursor.strftime("%Y%m%d"), options, limiter, counter):
            latest = cursor
            no_data_streak = 0
        else:
            no_data_streak += 1
        cursor += timedelta(days=1)
    return latest


def _target_dates(
    api_key: str,
    latest: date,
    options: FastBusCongestionOptions,
    limiter: RateLimiter,
    counter: ApiCounter,
) -> list[str]:
    dates: list[str] = []
    cursor = latest
    floor = latest - timedelta(days=options.lookback_days)
    while len(dates) < options.days and cursor >= floor:
        ymd = cursor.strftime("%Y%m%d")
        if ymd == latest.strftime("%Y%m%d") or _probe_date(api_key, ymd, options, limiter, counter):
            dates.append(ymd)
        cursor -= timedelta(days=1)
    if len(dates) < options.days:
        raise RuntimeError(f"only found {len(dates)} bus congestion target dates ending at {latest:%Y%m%d}")
    return dates


def _service_datetime(service_date: date, raw_hour: int) -> tuple[date, time]:
    if raw_hour < 0 or raw_hour > BUS_SERVICE_END_HOUR:
        raise ValueError("invalid bus service hour")
    if raw_hour < BUS_SERVICE_START_HOUR:
        return service_date + timedelta(days=1), time(raw_hour, 0)
    if raw_hour <= 23:
        return service_date, time(raw_hour, 0)
    return service_date + timedelta(days=1), time(raw_hour - 24, 0)


def _service_day_status(ymd: str) -> dict[str, Any]:
    date_value = date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))
    next_date = date_value + timedelta(days=1)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*)::int AS row_count,
                ARRAY_AGG(DISTINCT service_hour ORDER BY service_hour) AS hours
            FROM (
                SELECT
                    CASE
                        WHEN date = %s AND time >= time '04:00' THEN EXTRACT(HOUR FROM time)::int
                        WHEN date = %s AND time < time '04:00' THEN EXTRACT(HOUR FROM time)::int + 24
                    END AS service_hour
                FROM bus_congestion
                WHERE (date = %s AND time >= time '04:00')
                   OR (date = %s AND time < time '04:00')
            ) hourly
            WHERE service_hour IS NOT NULL
            """,
            [date_value, next_date, date_value, next_date],
        )
        row = cursor.fetchone()
    hours = set(row[1] or []) if row else set()
    missing_hours = [hour for hour in BUS_SERVICE_HOURS if hour not in hours]
    return {"row_count": int(row[0] or 0) if row else 0, "hours": sorted(hours), "missing_hours": missing_hours}


def _parse_row(row: dict[str, Any]) -> tuple[int, int, Decimal] | None:
    stop_raw = row.get("sttn_id") or row.get("STTN_ID")
    hour_raw = row.get("hh") or row.get("HH") or row.get("tmzon") or row.get("TMZON") or row.get("tzon") or row.get("TZON")
    value_raw = row.get("cgst") or row.get("CGST") or row.get("congestion") or row.get("CONGESTION")
    try:
        stop_id = int(str(stop_raw).strip())
        hour = int(str(hour_raw).strip())
        congestion = Decimal(str(value_raw).replace("%", "").strip())
    except Exception:
        return None
    if hour < 0 or hour > BUS_SERVICE_END_HOUR:
        return None
    return stop_id, hour, congestion


def _merge_rows(
    aggregate: dict[tuple[int, date, time], list[Decimal]],
    rows: list[dict[str, Any]],
    stop_id_map: dict[int, int],
    service_date: date,
) -> dict[str, int]:
    stats = {"raw": len(rows), "parsed": 0, "unmatched": 0, "bad": 0}
    for row in rows:
        parsed = _parse_row(row)
        if parsed is None:
            stats["bad"] += 1
            continue
        external_stop_id, hour, congestion = parsed
        stop_id = stop_id_map.get(external_stop_id)
        if stop_id is None:
            stats["unmatched"] += 1
            continue
        date_value, time_value = _service_datetime(service_date, hour)
        bucket = aggregate[(stop_id, date_value, time_value)]
        bucket[0] += congestion
        bucket[1] += Decimal(1)
        stats["parsed"] += 1
    return stats


def _create_stage_table() -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {STAGE_TABLE_NAME}")
        cursor.execute(
            f"""
            CREATE TEMP TABLE {STAGE_TABLE_NAME} (
                bus_stop_id bigint NOT NULL,
                date date NOT NULL,
                time time without time zone NOT NULL,
                total_congestion numeric(18,6) NOT NULL,
                sample_count integer NOT NULL,
                PRIMARY KEY (bus_stop_id, date, time)
            ) ON COMMIT PRESERVE ROWS
            """
        )


def _drop_stage_table() -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {STAGE_TABLE_NAME}")


def _upsert_stage_rows(aggregate: dict[tuple[int, date, time], list[Decimal]]) -> int:
    rows = [
        (stop_id, date_value, time_value, total, int(count))
        for (stop_id, date_value, time_value), (total, count) in sorted(aggregate.items())
        if count > 0
    ]
    if not rows:
        return 0

    with connection.cursor() as cursor:
        cursor.executemany(
            f"""
            INSERT INTO {STAGE_TABLE_NAME}
                (bus_stop_id, date, time, total_congestion, sample_count)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (bus_stop_id, date, time)
            DO UPDATE SET
                total_congestion = {STAGE_TABLE_NAME}.total_congestion + EXCLUDED.total_congestion,
                sample_count = {STAGE_TABLE_NAME}.sample_count + EXCLUDED.sample_count
            """,
            rows,
        )
    return len(rows)


def _stage_row_count() -> int:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {STAGE_TABLE_NAME}")
        row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _finalize_stage_rows() -> int:
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO bus_congestion (bus_stop_id, date, time, congestion)
                SELECT
                    bus_stop_id,
                    date,
                    time,
                    (total_congestion / NULLIF(sample_count, 0))::numeric(12,4)
                FROM {STAGE_TABLE_NAME}
                ON CONFLICT (bus_stop_id, date, time)
                DO UPDATE SET congestion = EXCLUDED.congestion
                """
            )
            inserted = cursor.rowcount
    return int(inserted or 0)


def _load_one_date(
    *,
    api_key: str,
    ymd: str,
    gu_codes: list[str],
    stop_id_map: dict[int, int],
    options: FastBusCongestionOptions,
    limiter: RateLimiter,
    counter: ApiCounter,
) -> dict[str, Any]:
    service_date = date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))
    service_status = _service_day_status(ymd)
    if service_status["row_count"] > 0 and not service_status["missing_hours"]:
        return {
            "ymd": ymd,
            "status": "skipped",
            "completed": True,
            "reason": "service_day_already_loaded",
            "existing_rows": service_status["row_count"],
            "hours": service_status["hours"],
        }

    stats = {"raw": 0, "parsed": 0, "unmatched": 0, "bad": 0, "pages": 0}
    total_pages = 0
    staged_batches = 0
    staged_aggregate_rows = 0

    def stage_rows(rows: list[dict[str, Any]]) -> None:
        nonlocal staged_batches, staged_aggregate_rows
        page_aggregate: dict[tuple[int, date, time], list[Decimal]] = defaultdict(lambda: [Decimal(0), Decimal(0)])
        row_stats = _merge_rows(page_aggregate, rows, stop_id_map, service_date)
        for key, value in row_stats.items():
            stats[key] += value
        if page_aggregate:
            staged_aggregate_rows += _upsert_stage_rows(page_aggregate)
            staged_batches += 1

    def page_chunks(items: list[tuple[str, int]]) -> list[list[tuple[str, int]]]:
        size = max(1, options.workers * PAGE_TASK_CHUNK_FACTOR)
        return [items[index : index + size] for index in range(0, len(items), size)]

    _create_stage_table()
    try:
        with ThreadPoolExecutor(max_workers=options.workers) as executor:
            first_futures = {
                executor.submit(
                    _fetch_page,
                    api_key=api_key,
                    ymd=ymd,
                    gu_code=gu_code,
                    page=1,
                    options=options,
                    limiter=limiter,
                    counter=counter,
                ): gu_code
                for gu_code in gu_codes
            }
            page_tasks: list[tuple[str, int]] = []
            for future in as_completed(first_futures):
                gu_code = first_futures[future]
                total, rows, _status = future.result()
                pages = int(math.ceil(total / options.page_size)) if total else 0
                total_pages += pages
                stats["pages"] += 1
                stage_rows(rows)
                for page in range(2, pages + 1):
                    page_tasks.append((gu_code, page))

            for chunk in page_chunks(page_tasks):
                futures = {
                    executor.submit(
                        _fetch_page,
                        api_key=api_key,
                        ymd=ymd,
                        gu_code=gu_code,
                        page=page,
                        options=options,
                        limiter=limiter,
                        counter=counter,
                    ): (gu_code, page)
                    for gu_code, page in chunk
                }
                for future in as_completed(futures):
                    _gu_code, _page = futures[future]
                    _total, rows, _status = future.result()
                    stats["pages"] += 1
                    stage_rows(rows)

        aggregate_rows = _stage_row_count()
        imported = 0 if options.dry_run else _finalize_stage_rows()
    finally:
        _drop_stage_table()

    return {
        "ymd": ymd,
        "status": "success",
        "completed": True,
        "imported": imported,
        "aggregate_rows": aggregate_rows,
        "staged_batches": staged_batches,
        "staged_aggregate_rows": staged_aggregate_rows,
        "total_pages": total_pages,
        "previous_missing_hours": service_status["missing_hours"],
        **stats,
    }


def update_bus_congestion_fast(options: FastBusCongestionOptions) -> dict[str, Any]:
    if options.dry_run:
        return {
            "target": "bus_congestion",
            "dry_run": True,
            "status": "success",
            "completed": True,
            "reason": "plan_only_no_api_probe",
            "retention_days": options.days,
        }

    api_keys = env_key_ring("PUBLIC_DATA_API_KEY")
    api_key = api_keys[0]
    limiter = RateLimiter(options.rps)
    counter = ApiCounter(options.max_api_calls)
    gu_codes = _gu_codes()
    stop_id_map, stop_map = _load_stop_id_map()
    if not gu_codes:
        raise RuntimeError("gu must be loaded before bus_congestion")
    if not stop_id_map:
        raise RuntimeError("bus_stop must be loaded before bus_congestion")

    latest = _latest_available_date(api_key, options, limiter, counter)
    target_dates = _target_dates(api_key, latest, options, limiter, counter)
    results: dict[str, Any] = {}
    completed_dates: list[str] = []
    failed_dates: dict[str, Any] = {}

    for ymd in target_dates:
        if _deadline_reached(options):
            return {
                "target": "bus_congestion",
                "dry_run": False,
                "status": "partial",
                "completed": False,
                "latest_ymd": latest.strftime("%Y%m%d"),
                "target_dates": target_dates,
                "completed_dates": completed_dates,
                "failed_dates": failed_dates,
                "results": results,
                "api_calls": counter.value,
                "reason": "deadline_reached",
            }
        try:
            item = _load_one_date(
                api_key=api_key,
                ymd=ymd,
                gu_codes=gu_codes,
                stop_id_map=stop_id_map,
                options=options,
                limiter=limiter,
                counter=counter,
            )
        except RateLimitedError:
            raise
        except TimeoutError as exc:
            if "deadline" in str(exc).lower():
                failed_dates[ymd] = {"type": type(exc).__name__, "message": str(exc)}
                results[ymd] = {
                    "ymd": ymd,
                    "status": "failed",
                    "completed": False,
                    "error": failed_dates[ymd],
                }
                return {
                    "target": "bus_congestion",
                    "dry_run": False,
                    "status": "partial",
                    "completed": False,
                    "latest_ymd": latest.strftime("%Y%m%d"),
                    "target_dates": target_dates,
                    "completed_dates": completed_dates,
                    "failed_dates": failed_dates,
                    "results": results,
                    "api_calls": counter.value,
                    "reason": "deadline_reached",
                }
            raise
        except Exception as exc:
            failed_dates[ymd] = {"type": type(exc).__name__, "message": str(exc)}
            item = {
                "ymd": ymd,
                "status": "failed",
                "completed": False,
                "error": failed_dates[ymd],
            }
        results[ymd] = item
        if item.get("completed"):
            completed_dates.append(ymd)

    if completed_dates:
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE bus_congestion")

    return {
        "target": "bus_congestion",
        "dry_run": False,
        "status": "partial" if failed_dates else "success",
        "completed": not failed_dates,
        "latest_ymd": latest.strftime("%Y%m%d"),
        "target_dates": target_dates,
        "completed_dates": completed_dates,
        "failed_dates": failed_dates,
        "results": results,
        "api_calls": counter.value,
        "retention_days": options.days,
        "rps": options.rps,
        "workers": options.workers,
        "stop_map": stop_map,
        "public_data_key_count": len(api_keys),
    }
