"""Fast EC2 bus_congestion loader used by scheduled_update.

Runs inside the backend container. Uses Django DB connection, not docker exec.
"""

from __future__ import annotations

import json
import math
import threading
import time as sleep_time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db import connection, transaction

from apps.public_data.api_keys import env_key_ring
from apps.public_data.bus.models import BusCongestion, BusStop
from apps.public_data.exceptions import RateLimitedError


BUS_URL = "https://apis.data.go.kr/1613000/RouteCongestionLevel/getRouteCongestionLevel"
PAGE_SIZE = 1000
RETENTION_DAYS = 14
DEFAULT_LOOKBACK_DAYS = 500
DISCOVERY_GUS = ("11680", "11500", "11710", "11440")


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


def _date_count(ymd: str) -> int:
    date_value = date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))
    return BusCongestion.objects.filter(date=date_value).count()


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
    if hour < 0 or hour > 23:
        return None
    return stop_id, hour, congestion


def _merge_rows(
    aggregate: dict[tuple[int, int], list[Decimal]],
    rows: list[dict[str, Any]],
    stop_ids: set[int],
) -> dict[str, int]:
    stats = {"raw": len(rows), "parsed": 0, "unmatched": 0, "bad": 0}
    for row in rows:
        parsed = _parse_row(row)
        if parsed is None:
            stats["bad"] += 1
            continue
        stop_id, hour, congestion = parsed
        if stop_id not in stop_ids:
            stats["unmatched"] += 1
            continue
        bucket = aggregate[(stop_id, hour)]
        bucket[0] += congestion
        bucket[1] += Decimal(1)
        stats["parsed"] += 1
    return stats


def _upsert_date_rows(ymd: str, aggregate: dict[tuple[int, int], list[Decimal]]) -> int:
    date_value = date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]))
    rows = [
        (stop_id, date_value, time(hour, 0), total / count)
        for (stop_id, hour), (total, count) in sorted(aggregate.items())
        if count > 0
    ]
    if not rows:
        return 0

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TEMP TABLE tmp_bus_congestion (
                    bus_stop_id bigint,
                    date date,
                    time time without time zone,
                    congestion numeric(8,3)
                ) ON COMMIT DROP
                """
            )
            cursor.executemany(
                """
                INSERT INTO tmp_bus_congestion (bus_stop_id, date, time, congestion)
                VALUES (%s, %s, %s, %s)
                """,
                rows,
            )
            cursor.execute(
                """
                INSERT INTO bus_congestion (bus_stop_id, date, time, congestion)
                SELECT bus_stop_id, date, time, congestion
                FROM tmp_bus_congestion
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
    stop_ids: set[int],
    options: FastBusCongestionOptions,
    limiter: RateLimiter,
    counter: ApiCounter,
) -> dict[str, Any]:
    existing = _date_count(ymd)
    if existing > 0:
        return {"ymd": ymd, "status": "skipped", "completed": True, "reason": "date_already_loaded", "existing_rows": existing}

    aggregate: dict[tuple[int, int], list[Decimal]] = defaultdict(lambda: [Decimal(0), Decimal(0)])
    stats = {"raw": 0, "parsed": 0, "unmatched": 0, "bad": 0, "pages": 0}
    total_pages = 0

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
            row_stats = _merge_rows(aggregate, rows, stop_ids)
            for key, value in row_stats.items():
                stats[key] += value
            for page in range(2, pages + 1):
                page_tasks.append((gu_code, page))

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
            for gu_code, page in page_tasks
        }
        for future in as_completed(futures):
            _gu_code, _page = futures[future]
            _total, rows, _status = future.result()
            stats["pages"] += 1
            row_stats = _merge_rows(aggregate, rows, stop_ids)
            for key, value in row_stats.items():
                stats[key] += value

    if options.dry_run:
        imported = 0
    else:
        imported = _upsert_date_rows(ymd, aggregate)

    return {
        "ymd": ymd,
        "status": "success",
        "completed": True,
        "imported": imported,
        "aggregate_rows": len(aggregate),
        "total_pages": total_pages,
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
    stop_ids = _existing_stop_ids()
    if not gu_codes:
        raise RuntimeError("gu must be loaded before bus_congestion")
    if not stop_ids:
        raise RuntimeError("bus_stop must be loaded before bus_congestion")

    latest = _latest_available_date(api_key, options, limiter, counter)
    target_dates = _target_dates(api_key, latest, options, limiter, counter)
    results: dict[str, Any] = {}
    completed_dates: list[str] = []

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
                "results": results,
                "api_calls": counter.value,
                "reason": "deadline_reached",
            }
        item = _load_one_date(
            api_key=api_key,
            ymd=ymd,
            gu_codes=gu_codes,
            stop_ids=stop_ids,
            options=options,
            limiter=limiter,
            counter=counter,
        )
        results[ymd] = item
        if item.get("completed"):
            completed_dates.append(ymd)

    with connection.cursor() as cursor:
        cursor.execute("ANALYZE bus_congestion")

    return {
        "target": "bus_congestion",
        "dry_run": False,
        "status": "success",
        "completed": True,
        "latest_ymd": latest.strftime("%Y%m%d"),
        "target_dates": target_dates,
        "completed_dates": completed_dates,
        "results": results,
        "api_calls": counter.value,
        "retention_days": options.days,
        "rps": options.rps,
        "workers": options.workers,
        "public_data_key_count": len(api_keys),
    }
