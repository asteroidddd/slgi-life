"""Bus public-data updater for the current capston schema."""

from __future__ import annotations

import json
import os
import time as sleep_time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.contrib.gis.geos import Point
from django.db import transaction

from apps.public_data.bus.models import BusCongestion, BusStop
from apps.public_data.exceptions import RateLimitedError, is_rate_limited_code, is_rate_limited_text
from apps.public_data.regions.models import Adong, Gu, Ldong
from apps.public_data.state import dataset_state, load_state, record_dataset_result, save_state


SEOUL_BUS_STOP_URL = (
    "http://openapi.seoul.go.kr:8088/{key}/json/busStopLocationXyInfo/{start}/{end}/"
)
PUBLIC_DATA_BASE_URL = "https://apis.data.go.kr"
BUS_CONGESTION_PATH = "/1613000/RouteCongestionLevel/getRouteCongestionLevel"
PAGE_SIZE = 1000
BUS_CONGESTION_RETENTION_DAYS = 31
BUS_CONGESTION_LAG_DAYS = 15


@dataclass(frozen=True)
class BusUpdateOptions:
    dry_run: bool = True
    update_stops: bool = True
    update_congestion: bool = True
    start_date: date | None = None
    end_date: date | None = None
    limit: int | None = None
    request_interval_seconds: float = 0.2
    request_timeout_seconds: float = 40.0


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _get(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.isdigit():
        return str(int(text))
    return text


def _request_json(url: str, *, timeout: float) -> Any:
    req = Request(url, headers={"User-Agent": "capston-public-data-updater/0.1"})
    try:
        with urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8", errors="replace"))
    except HTTPError as exc:
        if exc.code == 429:
            raise RateLimitedError(f"HTTP 429: {url}") from exc
        raise RuntimeError(f"HTTP {exc.code}: {url}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"request failed: {type(exc).__name__}: {url}") from exc


def _seoul_bus_stop_rows(api_key: str, options: BusUpdateOptions):
    start = 1
    fetched = 0
    while True:
        end = start + PAGE_SIZE - 1
        payload = _request_json(
            SEOUL_BUS_STOP_URL.format(key=api_key, start=start, end=end),
            timeout=options.request_timeout_seconds,
        )
        body = payload.get("busStopLocationXyInfo") or {}
        result = body.get("RESULT") or {}
        if str(result.get("CODE", "")).startswith("ERROR"):
            if is_rate_limited_text(result):
                raise RateLimitedError(f"Seoul bus stop API rate limited: {result}")
            raise RuntimeError(f"Seoul bus stop API error: {result}")
        rows = body.get("row") or []
        for row in rows:
            if options.limit is not None and fetched >= options.limit:
                return
            fetched += 1
            yield row
        total = int(body.get("list_total_count") or 0)
        if not rows or start + len(rows) > total:
            return
        start += len(rows)
        if options.request_interval_seconds:
            sleep_time.sleep(options.request_interval_seconds)


def _public_data_json(
    api_key: str,
    path: str,
    params: dict[str, str],
    options: BusUpdateOptions,
):
    query = urlencode({"serviceKey": api_key, **params}, doseq=True, safe="%")
    return _request_json(
        f"{PUBLIC_DATA_BASE_URL}{path}?{query}",
        timeout=options.request_timeout_seconds,
    )


def _response_items(payload: Any) -> tuple[int, list[dict[str, Any]]]:
    response = payload.get("response", {}) if isinstance(payload, dict) else {}
    header = response.get("header", {}) if isinstance(response, dict) else {}
    result_code = header.get("resultCode")
    result_msg = header.get("resultMsg")
    if is_rate_limited_code(result_code) or is_rate_limited_text(result_msg):
        raise RateLimitedError(f"bus congestion API rate limited: {result_code} {result_msg}")
    body = response.get("body", {}) if isinstance(response, dict) else {}
    items = body.get("items", {})
    rows = items.get("item", []) if isinstance(items, dict) else items
    if isinstance(rows, dict):
        rows = [rows]
    if rows is None:
        rows = []
    return int(body.get("totalCount") or len(rows) or 0), list(rows)


def _find_region(point: Point) -> tuple[Ldong | None, Adong | None]:
    return (
        Ldong.objects.filter(boundary__covers=point).order_by("area_m2").first(),
        Adong.objects.filter(boundary__covers=point).order_by("area_m2").first(),
    )


def update_bus_stops(options: BusUpdateOptions) -> dict[str, Any]:
    api_key = _require_env("SEOUL_API_KEY")
    checked = created = updated = skipped = 0
    skip_reasons = {"bad_coord": 0, "missing_required": 0}

    with transaction.atomic():
        for row in _seoul_bus_stop_rows(api_key, options):
            checked += 1
            stop_id = _normalize_id(_get(row, "NODE_ID", "STTN_ID", "BUSSTOP_ID"))
            name = str(_get(row, "STOPS_NM", "STTN_NM", "BUSSTOP_NM") or "").strip()
            stop_number = str(_get(row, "STOPS_NO", "STTN_ARS_NO", "ARS_ID") or "").strip() or None
            try:
                lon = float(_get(row, "XCRD", "X", "LON"))
                lat = float(_get(row, "YCRD", "Y", "LAT"))
            except (TypeError, ValueError):
                skipped += 1
                skip_reasons["bad_coord"] += 1
                continue
            if not stop_id or not name:
                skipped += 1
                skip_reasons["missing_required"] += 1
                continue

            point = Point(lon, lat, srid=4326)
            ldong, adong = _find_region(point)
            if not options.dry_run:
                _, was_created = BusStop.objects.update_or_create(
                    id=stop_id,
                    defaults={
                        "name": name[:100],
                        "stop_number": stop_number,
                        "location": point,
                        "ldong_id": ldong.ldong_code if ldong else None,
                        "adong_id": adong.adong_code if adong else None,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

    return {
        "checked": checked,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "dry_run": options.dry_run,
        "skip_reasons": skip_reasons,
    }


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _date_range(start: date, end: date) -> list[date]:
    out = []
    current = start
    while current <= end:
        out.append(current)
        current += timedelta(days=1)
    return out


def _missing_congestion_dates(start: date, end: date, completed_dates: set[str]) -> list[date]:
    dates = _date_range(start, end)
    return [day for day in dates if day.isoformat() not in completed_dates]


def _congestion_window(options: BusUpdateOptions) -> tuple[date | None, date | None, dict[str, Any]]:
    today = date.today()
    retention_start = today - timedelta(days=BUS_CONGESTION_RETENTION_DAYS)
    default_end = today - timedelta(days=BUS_CONGESTION_LAG_DAYS)

    previous = dataset_state("bus").get("bus_congestion", {})
    last_success_date = _parse_date(previous.get("last_success_date")) if previous else None

    if options.start_date is not None:
        start = options.start_date
    elif last_success_date is not None:
        start = max(retention_start, last_success_date + timedelta(days=1))
    else:
        start = retention_start
    end = options.end_date or default_end

    meta = {
        "retention_days": BUS_CONGESTION_RETENTION_DAYS,
        "lag_days": BUS_CONGESTION_LAG_DAYS,
        "retention_start": retention_start.isoformat(),
        "previous_last_success_date": last_success_date.isoformat()
        if last_success_date
        else None,
    }
    if start > end:
        return None, None, meta
    return start, end, meta


def update_bus_congestion(options: BusUpdateOptions) -> dict[str, Any]:
    api_key = _require_env("PUBLIC_DATA_API_KEY")
    start, end, window_meta = _congestion_window(options)
    if start is None or end is None:
        return {
            "status": "success",
            "completed": True,
            "checked": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "processed_dates": [],
            "dry_run": options.dry_run,
            "window": window_meta | {"start": None, "end": None},
            "skip_reasons": {},
        }

    previous_congestion = dataset_state("bus").get("bus_congestion", {})
    completed_dates = set(previous_congestion.get("completed_dates") or [])
    target_dates = sorted(_missing_congestion_dates(start, end, completed_dates), reverse=True)
    if not target_dates:
        return {
            "status": "success",
            "completed": True,
            "checked": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "deleted_old": 0,
            "processed_dates": [],
            "completed_dates": [],
            "dry_run": options.dry_run,
            "window": window_meta | {"start": start.isoformat(), "end": end.isoformat()},
            "skip_reasons": {},
            "reason": "no_missing_dates",
        }

    gu_codes = list(Gu.objects.order_by("gu_code").values_list("gu_code", flat=True))
    existing_stop_ids = set(BusStop.objects.values_list("id", flat=True))
    checked = created = updated = skipped = 0
    skip_reasons = {"bad_row": 0, "missing_bus_stop": 0}
    processed_dates: list[str] = []
    completed = False

    try:
        for day in target_dates:
            ymd = day.strftime("%Y%m%d")
            for gu_code in gu_codes:
                page = 1
                while True:
                    payload = _public_data_json(
                        api_key,
                        BUS_CONGESTION_PATH,
                        {
                            "pageNo": str(page),
                            "numOfRows": "1000",
                            "ctpv_cd": "11",
                            "sgg_cd": gu_code,
                            "opr_ymd": ymd,
                            "dataType": "JSON",
                        },
                        options,
                    )
                    total, rows = _response_items(payload)
                    if not rows:
                        break

                    aggregate: dict[tuple[str, date, time], list[Decimal]] = defaultdict(list)
                    for row in rows:
                        checked += 1
                        try:
                            stop_id = _normalize_id(_get(row, "sttn_id", "STTN_ID"))
                            raw_hour = _get(row, "hh", "HH", "tmzon", "TMZON", "TZON")
                            hour = int(str(raw_hour).strip())
                            if not 0 <= hour <= 23:
                                raise ValueError("invalid hour")
                            value = Decimal(
                                str(_get(row, "cgst", "CGST", "congestion", "CONGESTION"))
                                .replace("%", "")
                                .strip()
                            )
                        except (TypeError, ValueError, InvalidOperation):
                            skipped += 1
                            skip_reasons["bad_row"] += 1
                            continue
                        if stop_id not in existing_stop_ids:
                            skipped += 1
                            skip_reasons["missing_bus_stop"] += 1
                            continue
                        aggregate[(stop_id, day, time(hour, 0))].append(value)

                    if not options.dry_run:
                        for (stop_id, date_value, time_value), values in aggregate.items():
                            with transaction.atomic():
                                _, was_created = BusCongestion.objects.update_or_create(
                                    bus_stop_id=stop_id,
                                    date=date_value,
                                    time=time_value,
                                    defaults={"congestion": sum(values) / Decimal(len(values))},
                                )
                            if was_created:
                                created += 1
                            else:
                                updated += 1

                    if options.limit is not None and checked >= options.limit:
                        break
                    if total and page * PAGE_SIZE >= total:
                        break
                    page += 1
                    if options.request_interval_seconds:
                        sleep_time.sleep(options.request_interval_seconds)
                if options.limit is not None and checked >= options.limit:
                    break
            processed_dates.append(day.isoformat())
            if options.limit is not None and checked >= options.limit:
                break
        else:
            completed = checked > 0

        deleted_old = 0
        if not options.dry_run and completed:
            cutoff = date.today() - timedelta(days=BUS_CONGESTION_RETENTION_DAYS)
            deleted_old, _ = BusCongestion.objects.filter(date__lt=cutoff).delete()
    except RateLimitedError as exc:
        return {
            "status": "rate_limited",
            "completed": False,
            "checked": checked,
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "deleted_old": 0,
            "processed_dates": processed_dates,
            "completed_dates": processed_dates,
            "dry_run": options.dry_run,
            "window": window_meta | {"start": start.isoformat(), "end": end.isoformat()},
            "skip_reasons": skip_reasons,
            "error": str(exc),
        }

    return {
        "status": "success" if completed else "partial",
        "completed": completed,
        "checked": checked,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "deleted_old": deleted_old if not options.dry_run else 0,
        "processed_dates": processed_dates,
        "completed_dates": processed_dates,
        "dry_run": options.dry_run,
        "window": window_meta | {"start": start.isoformat(), "end": end.isoformat()},
        "skip_reasons": skip_reasons,
    }


def update(options: BusUpdateOptions) -> dict[str, Any]:
    result: dict[str, Any] = {
        "dataset": "bus",
        "dry_run": options.dry_run,
        "bus_stop": None,
        "bus_congestion": None,
    }
    try:
        if options.update_stops:
            result["bus_stop"] = update_bus_stops(options)
        if options.update_congestion:
            result["bus_congestion"] = update_bus_congestion(options)
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if not options.dry_run:
            record_dataset_result("bus", result)
        raise

    if not options.dry_run:
        record_dataset_result("bus", result)
        if result["bus_congestion"]:
            window = result["bus_congestion"].get("window") or {}
            state = load_state()
            bus_state = state.setdefault("datasets", {}).setdefault("bus", {})
            previous_congestion = bus_state.setdefault("bus_congestion", {})
            retention_start = window.get("retention_start")
            previous_dates = set(previous_congestion.get("completed_dates") or [])
            current_dates = set(result["bus_congestion"].get("completed_dates") or [])
            merged_dates = sorted(
                day for day in previous_dates | current_dates if not retention_start or day >= retention_start
            )
            previous_congestion.update(
                {
                    "completed_dates": merged_dates,
                    "retention_days": BUS_CONGESTION_RETENTION_DAYS,
                    "lag_days": BUS_CONGESTION_LAG_DAYS,
                }
            )
            if window.get("end") and result["bus_congestion"].get("completed"):
                previous_congestion["last_success_date"] = window["end"]
                previous_congestion["last_completed_at"] = bus_state.get("last_success_at")
            save_state(state)
    return result
