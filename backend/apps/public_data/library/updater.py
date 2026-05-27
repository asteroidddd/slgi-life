"""Library public-data updater for the current capston schema."""

from __future__ import annotations

import json
import os
import re
import time as sleep_time
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.contrib.gis.geos import Point
from django.db import transaction

from apps.public_data.exceptions import RateLimitedError, is_rate_limited_text
from apps.public_data.library.models import Library, LibraryHours
from apps.public_data.regions.models import Adong, Ldong
from apps.public_data.state import load_state, record_dataset_result, save_state


SEOUL_OPEN_DATA_BASE_URL = "http://openapi.seoul.go.kr:8088"
SEOUL_LIBRARY_SERVICES = {
    "SeoulPublicLibraryInfo": "공공도서관",
    "SeoulSmallLibraryInfo": "작은도서관",
}
VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"
PAGE_SIZE = 1000

DAY_TYPES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI"]
WEEKEND = ["SAT", "SUN"]
DAY_TO_KEY = {"월": "MON", "화": "TUE", "수": "WED", "목": "THU", "금": "FRI", "토": "SAT", "일": "SUN"}
WD = "월화수목금토일"


@dataclass(frozen=True)
class TimeRange:
    open_time: time
    close_time: time

    @property
    def minutes(self) -> int:
        return (
            self.close_time.hour * 60
            + self.close_time.minute
            - self.open_time.hour * 60
            - self.open_time.minute
        )


@dataclass(frozen=True)
class LibraryUpdateOptions:
    dry_run: bool = True
    limit: int | None = None
    request_interval_seconds: float = 0.2
    request_timeout_seconds: float = 40.0


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _optional_env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def _get(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


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


def _seoul_rows(api_key: str, service: str, options: LibraryUpdateOptions):
    start = 1
    while True:
        end = start + PAGE_SIZE - 1
        url = f"{SEOUL_OPEN_DATA_BASE_URL}/{api_key}/json/{service}/{start}/{end}/"
        payload = _request_json(url, timeout=options.request_timeout_seconds)
        body = payload.get(service) or {}
        result = body.get("RESULT") or {}
        if str(result.get("CODE", "")).startswith("ERROR"):
            if is_rate_limited_text(result):
                raise RateLimitedError(f"Seoul library API rate limited: {service}: {result}")
            raise RuntimeError(f"Seoul library API error: {service}: {result}")
        rows = body.get("row") or []
        if not rows:
            return
        for row in rows:
            yield row
        total = int(body.get("list_total_count") or 0)
        if start + len(rows) > total:
            return
        start += len(rows)
        if options.request_interval_seconds:
            sleep_time.sleep(options.request_interval_seconds)


def _find_region(point: Point) -> tuple[Ldong | None, Adong | None]:
    return (
        Ldong.objects.filter(boundary__covers=point).order_by("area_m2").first(),
        Adong.objects.filter(boundary__covers=point).order_by("area_m2").first(),
    )


def _point_from_row(row: dict[str, Any]) -> Point | None:
    try:
        lat = float(_get(row, "XCNTS", "LAT", "위도"))
        lon = float(_get(row, "YDNTS", "LON", "경도"))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return Point(lon, lat, srid=4326)


def _address_from_row(row: dict[str, Any]) -> str:
    return str(
        _get(
            row,
            "ADRES",
            "ADDRESS",
            "ADDR",
            "LBRRY_ADRES",
            "RDNMADR",
            "도로명주소",
            "주소",
        )
        or ""
    ).strip()


def _geocode_address(address: str, options: LibraryUpdateOptions) -> Point | None:
    key = _optional_env("V_WORLD_API_KEY")
    if not key or not address:
        return None
    for category in ("road", "parcel"):
        query = urlencode(
            {
                "service": "search",
                "request": "search",
                "version": "2.0",
                "query": address,
                "type": "address",
                "category": category,
                "format": "json",
                "crs": "EPSG:4326",
                "size": "1",
                "page": "1",
                "key": key,
            }
        )
        payload = _request_json(
            f"{VWORLD_SEARCH_URL}?{query}",
            timeout=options.request_timeout_seconds,
        )
        items = payload.get("response", {}).get("result", {}).get("items", [])
        if not items:
            continue
        point = items[0].get("point") or {}
        try:
            lon = float(point.get("x"))
            lat = float(point.get("y"))
        except (TypeError, ValueError):
            continue
        return Point(lon, lat, srid=4326)
    return None


def _fix_time_text(value: str) -> str:
    text = value.replace("∼", "~").replace("〜", "~").replace("～", "~").replace("－", "-")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"(\d{1,2})\s*:\s*:\s*(\d{2})", r"\1:\2", text)
    text = re.sub(r"(?<!\d)(\d{2})(\d{2})\s*[~\-]\s*(\d{2})(\d{2})(?!\d)", r"\1:\2~\3:\4", text)
    text = re.sub(r"(\d{1,2})\s*:\s*(\d)(?!\d)", r"\1:\g<2>0", text)
    text = re.sub(r"(\d{1,2})\s*시(?!\s*\d)", r"\1:00", text)
    return text


def _make_time(hour: str, minute: str | None) -> time | None:
    try:
        h = int(hour)
        m = int(minute or 0)
    except ValueError:
        return None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return time(h, m)


def _extract_ranges(value: str) -> list[TimeRange]:
    text = _fix_time_text(value)
    ranges: list[TimeRange] = []
    for match in re.finditer(r"(\d{1,2})\s*:?\s*(\d{2})?\s*[~\-]\s*(\d{1,2})\s*:?\s*(\d{2})?", text):
        open_t = _make_time(match.group(1), match.group(2))
        close_t = _make_time(match.group(3), match.group(4))
        if not open_t or not close_t or open_t >= close_t:
            continue
        ranges.append(TimeRange(open_t, close_t))
    return ranges


def _longest(ranges: list[TimeRange]) -> TimeRange | None:
    return max(ranges, key=lambda item: item.minutes) if ranges else None


def _merged(ranges: list[TimeRange]) -> TimeRange | None:
    if not ranges:
        return None
    return TimeRange(min(item.open_time for item in ranges), max(item.close_time for item in ranges))


def _op_is_closed(value: str) -> bool:
    if value in {"", "-", "휴관중"}:
        return True
    if re.match(r"^\s*휴관(중?\s|\()", value):
        return True
    if re.search(r"평일\s*:\s*휴관(중?\s|,)", value) and re.search(r"주말\s*:\s*휴관(중?\s|$)", value):
        return True
    return re.fullmatch(r"\s*평일\s*:\s*,\s*주말\s*:\s*", value) is not None


def _op_is_season(value: str) -> bool:
    keys = ["동절기", "하절기", "계절", "춘계", "동계", "하계", "추계", "방학기간"]
    return any(key in value for key in keys) or re.search(r"\d{1,2}\s*월\s*[~\-]\s*\d{1,2}\s*월", value) is not None


def _op_is_lunch(value: str) -> bool:
    if "점심" in value or "중식" in value:
        return True
    return re.search(r"12\s*:\s*\d{2}\s*[~\-]\s*13\s*:\s*\d{2}", value) is not None


def _op_is_irregular(value: str) -> bool:
    typo = (
        re.search(r"(?<!\d)(\d{2})(\d{2})\s*[~\-]\s*(\d{2})(\d{2})(?!\d)", value) is not None
        or re.search(r"\d{1,2}\s*:\s*\d(?!\d)", value) is not None
        or re.search(r"\d{2}\s*:\s*:\s*\d{2}", value) is not None
    )
    room = any(
        key in value
        for key in [
            "어린이자료실",
            "종합자료실",
            "디지털자료실",
            "열람실",
            "이용자료실",
            "부분실",
        ]
    )
    return bool(_op_is_season(value) or _op_is_lunch(value) or typo or room or "*" in value)


def _resolve_range(segment: str, *, is_lunch: bool, is_season: bool) -> TimeRange | None:
    ranges = _extract_ranges(segment)
    if not ranges:
        return None
    if is_lunch and len(ranges) >= 2:
        return _merged(ranges)
    if is_season and len(ranges) >= 2:
        return _longest(ranges)
    return ranges[0]


def _parse_op_time(value: str | None) -> tuple[dict[str, tuple[time, time, bool]], str | None]:
    raw = (value or "").strip()
    if not raw:
        return {}, None
    if _op_is_closed(raw):
        return {}, f"운영시간 원문: {raw}"

    fixed = _fix_time_text(raw)
    ranges = _extract_ranges(fixed)
    is_season = _op_is_season(raw)
    is_lunch = _op_is_lunch(raw)
    irregular = _op_is_irregular(raw)
    remarks: list[str] = []
    if is_season:
        remarks.append("시즌별 운영시간 포함")
    if is_lunch:
        remarks.append("점심시간/중식 운영정보 포함")
    if irregular:
        remarks.append(f"운영시간 원문 확인 필요: {raw[:120]}")
    if not ranges:
        return {}, f"운영시간 파싱 실패: {raw[:200]}"

    result: dict[str, tuple[time, time, bool]] = {}

    def put(days: list[str], segment: str) -> None:
        picked = _resolve_range(segment, is_lunch=is_lunch, is_season=is_season)
        if picked:
            for day in days:
                result[day] = (picked.open_time, picked.close_time, irregular)

    weekday_match = re.search(r"평일\s*[:：]?\s*([^,]+?)(?=\s*[,/]\s*주말|\s*$)", fixed)
    weekend_match = re.search(r"주말\s*[:：]?\s*([^,]+)", fixed)
    everyday_match = re.search(r"매일\s*[:：]?\s*([^.,]+)", fixed)
    everyday_combo = re.search(r"평일\s*[,/]\s*주말\s*[:：]?\s*([^.,]+)", fixed)
    range_match = re.search(rf"매주\s*([{WD}])\s*[~\-]\s*([{WD}])\s*[:：]?\s*([^,]+)", fixed)

    if everyday_combo:
        put(DAY_TYPES, everyday_combo.group(1))
    elif everyday_match and not (weekday_match or weekend_match):
        put(DAY_TYPES, everyday_match.group(1))
    else:
        if weekday_match:
            put(WEEKDAYS, weekday_match.group(1))
        if weekend_match:
            put(WEEKEND, weekend_match.group(1))

    if not result and range_match:
        picked = _resolve_range(range_match.group(3), is_lunch=is_lunch, is_season=is_season)
        if picked:
            days = list(WD)
            start = days.index(range_match.group(1))
            end = days.index(range_match.group(2))
            if start <= end:
                for day in days[start : end + 1]:
                    result[DAY_TO_KEY[day]] = (picked.open_time, picked.close_time, irregular)

    if not result:
        picked = _merged(ranges) if is_lunch and len(ranges) >= 2 else _longest(ranges) if is_season else ranges[0]
        days = DAY_TYPES if is_lunch or is_season else WEEKDAYS
        for day in days:
            result[day] = (picked.open_time, picked.close_time, irregular)

    for match in re.finditer(rf"([{WD}])요일\s*[:：]?\s*((\d{{1,2}}\s*:\s*\d{{2}}\s*[~\-]\s*\d{{1,2}}\s*:\s*\d{{2}}))", fixed):
        picked = _resolve_range(match.group(2), is_lunch=is_lunch, is_season=is_season)
        if picked:
            result[DAY_TO_KEY[match.group(1)]] = (picked.open_time, picked.close_time, irregular)

    return result, "; ".join(remarks) if remarks else None


def _parse_close_date(value: str | None) -> tuple[set[str], str | None, bool]:
    raw = (value or "").strip()
    if not raw:
        return set(), None, False
    if "휴관중" in raw or re.search(r"휴관\s*[\(:]", raw):
        return set(DAY_TYPES), f"휴관 원문: {raw[:120]}", True

    closed_days: set[str] = set()
    remarks: list[str] = []
    if any(key in raw for key in ["첫째", "둘째", "셋째", "넷째", "다섯째", "마지막", "1주", "2주", "3주", "4주", "5주"]):
        remarks.append(f"비정기/주차별 휴관: {raw[:120]}")
    else:
        match = re.search(r"매주\s*([^.,()]+)", raw)
        days_text = match.group(1) if match else raw
        for ko, day in DAY_TO_KEY.items():
            if f"{ko}요일" in days_text or re.search(rf"(^|[\s,/]){ko}($|[\s,/])", days_text):
                closed_days.add(day)

    if any(key in raw for key in ["공휴일", "명절", "설날", "추석", "근로자의날", "성탄절"]):
        remarks.append("공휴일/특정일 휴관 포함")
    return closed_days, "; ".join(remarks) if remarks else None, bool(remarks)


def _library_type(row: dict[str, Any], service: str) -> str:
    raw = str(_get(row, "LBRRY_SE_NAME", "LIBRARY_TYPE") or "").strip()
    if raw in {"공공도서관", "작은도서관"}:
        return raw
    return SEOUL_LIBRARY_SERVICES[service]


def _row_to_record(
    row: dict[str, Any],
    service: str,
    options: LibraryUpdateOptions,
    skip_reasons: dict[str, int],
) -> dict[str, Any] | None:
    seq = str(_get(row, "LBRRY_SEQ_NO", "LBRRY_ID") or "").strip()
    name = str(_get(row, "LBRRY_NAME", "NAME") or "").strip()
    if not seq or not name:
        skip_reasons["missing_required"] += 1
        return None

    point = _point_from_row(row)
    ldong = adong = None
    if point:
        ldong, adong = _find_region(point)

    if not (point and ldong and adong):
        address = _address_from_row(row)
        geocoded = _geocode_address(address, options)
        if geocoded:
            point = geocoded
            ldong, adong = _find_region(point)
            skip_reasons["geocode_used"] += 1
        elif address and not _optional_env("V_WORLD_API_KEY"):
            skip_reasons["geocode_missing_key"] += 1
        elif address:
            skip_reasons["geocode_failed"] += 1

    if not point:
        skip_reasons["bad_coord"] += 1
        return None
    if not (ldong and adong):
        skip_reasons["region_not_found"] += 1
        return None

    op_raw = str(_get(row, "OP_TIME", "OPER_TIME", "운영시간") or "").strip()
    close_raw = str(_get(row, "FDRM_CLOSE_DATE", "CLOSE_DATE", "휴관일") or "").strip()
    op_hours, op_remark = _parse_op_time(op_raw)
    closed_days, close_remark, close_irregular = _parse_close_date(close_raw)
    for day in closed_days:
        op_hours.pop(day, None)

    remarks: list[str] = []
    for value in (op_remark, close_remark):
        if value and value not in remarks:
            remarks.append(value)
    if op_raw and not op_hours and not op_remark:
        remarks.append(f"운영시간 파싱 실패: {op_raw[:200]}")

    hours = [
        (day, open_t, close_t, irregular or close_irregular)
        for day, (open_t, close_t, irregular) in sorted(op_hours.items())
    ]

    return {
        "id": seq[:20],
        "library": {
            "name": name[:100],
            "library_type": _library_type(row, service),
            "remark": "; ".join(remarks)[:2000] or None,
            "location": point,
            "ldong_id": ldong.ldong_code,
            "adong_id": adong.adong_code,
        },
        "hours": hours,
    }


def update_libraries(options: LibraryUpdateOptions) -> dict[str, Any]:
    api_key = _require_env("SEOUL_API_KEY")
    checked = loaded = created = updated = skipped = hour_rows = 0
    skip_reasons = {
        "bad_coord": 0,
        "geocode_failed": 0,
        "geocode_missing_key": 0,
        "geocode_used": 0,
        "missing_required": 0,
        "region_not_found": 0,
    }
    service_stats: dict[str, dict[str, int]] = {
        service: {"checked": 0, "loaded": 0, "skipped": 0} for service in SEOUL_LIBRARY_SERVICES
    }
    seen_source_ids: set[str] = set()
    completed = False

    with transaction.atomic():
        for service in SEOUL_LIBRARY_SERVICES:
            for row in _seoul_rows(api_key, service, options):
                checked += 1
                service_stats[service]["checked"] += 1
                source_id = str(_get(row, "LBRRY_SEQ_NO", "LBRRY_ID") or "").strip()
                if source_id:
                    seen_source_ids.add(source_id[:20])
                record = _row_to_record(row, service, options, skip_reasons)
                if not record:
                    skipped += 1
                    service_stats[service]["skipped"] += 1
                else:
                    if not options.dry_run:
                        library, was_created = Library.objects.update_or_create(
                            id=record["id"],
                            defaults=record["library"],
                        )
                        LibraryHours.objects.filter(library=library).delete()
                        LibraryHours.objects.bulk_create(
                            [
                                LibraryHours(
                                    library=library,
                                    day_type=day,
                                    time_open=open_t,
                                    time_close=close_t,
                                    is_irregular=irregular,
                                )
                                for day, open_t, close_t, irregular in record["hours"]
                            ]
                        )
                        if was_created:
                            created += 1
                        else:
                            updated += 1
                    loaded += 1
                    hour_rows += len(record["hours"])
                    service_stats[service]["loaded"] += 1

                if options.limit is not None and checked >= options.limit:
                    break
            if options.limit is not None and checked >= options.limit:
                break
        else:
            completed = checked > 0 and loaded > 0

        deleted_missing = 0
        if completed and not options.dry_run:
            missing_queryset = Library.objects.exclude(id__in=seen_source_ids)
            deleted_missing = missing_queryset.count()
            missing_queryset.delete()

    return {
        "status": "success" if completed else "partial",
        "completed": completed,
        "checked": checked,
        "loaded": loaded,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "deleted_missing": deleted_missing if not options.dry_run else 0,
        "library_hours": hour_rows,
        "dry_run": options.dry_run,
        "services": service_stats,
        "skip_reasons": skip_reasons,
    }


def update(options: LibraryUpdateOptions) -> dict[str, Any]:
    result: dict[str, Any] = {
        "dataset": "library",
        "dry_run": options.dry_run,
        "library": None,
    }
    try:
        result["library"] = update_libraries(options)
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if not options.dry_run:
            record_dataset_result("library", result)
        raise

    if not options.dry_run:
        record_dataset_result("library", result)
        if result["library"] and result["library"].get("completed"):
            state = load_state()
            library_state = state.setdefault("datasets", {}).setdefault("library", {})
            library_state["snapshot"] = {
                "last_success_date": None,
                "checked": result["library"]["checked"],
                "loaded": result["library"]["loaded"],
                "library_hours": result["library"]["library_hours"],
                "deleted_missing": result["library"]["deleted_missing"],
                "services": result["library"]["services"],
            }
            save_state(state)
    return result
