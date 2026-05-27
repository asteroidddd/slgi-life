"""Rent-deal public-data updater for the current capston schema."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import socket
import time as sleep_time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.contrib.gis.geos import Point
from django.db import transaction

from apps.public_data.exceptions import RateLimitedError, is_rate_limited_code, is_rate_limited_text
from apps.public_data.regions.models import Adong, Ldong
from apps.public_data.rent_deal.models import RentDeal, RentDealLdongAdongMap
from apps.public_data.state import dataset_state, load_state, record_dataset_result, save_state


PUBLIC_DATA_BASE_URL = "https://apis.data.go.kr"
V_WORLD_GEOCODE_URL = "https://api.vworld.kr/req/address"
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "rent_deal_ldong_adong_map.csv"
DEFAULT_START_YM = "201101"
PAGE_SIZE = 1000

RENT_ENDPOINTS = {
    "아파트": "/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
    "오피스텔": "/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent",
    "연립다세대": "/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent",
    "단독다가구": "/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent",
}


@dataclass(frozen=True)
class RentDealsUpdateOptions:
    dry_run: bool = True
    force: bool = False
    limit: int | None = None
    start_ym: str | None = None
    end_ym: str | None = None
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


def _validate_ym(value: str) -> str:
    if len(value) != 6 or not value.isdigit():
        raise ValueError(f"YYYYMM is required: {value}")
    month = int(value[4:])
    if int(value[:4]) < 2000 or month < 1 or month > 12:
        raise ValueError(f"invalid YYYYMM: {value}")
    return value


def _current_ym(today: date | None = None) -> str:
    today = today or date.today()
    return f"{today.year:04d}{today.month:02d}"


def _next_ym(value: str) -> str:
    year = int(value[:4])
    month = int(value[4:])
    if month == 12:
        return f"{year + 1:04d}01"
    return f"{year:04d}{month + 1:02d}"


def _iter_months(start_ym: str, end_ym: str) -> list[str]:
    start_ym = _validate_ym(start_ym)
    end_ym = _validate_ym(end_ym)
    if start_ym > end_ym:
        return []
    months = []
    current = start_ym
    while current <= end_ym:
        months.append(current)
        current = _next_ym(current)
    return months


def _month_bounds(ym: str) -> tuple[date, date]:
    start = date(int(ym[:4]), int(ym[4:]), 1)
    next_month = _next_ym(ym)
    end = date(int(next_month[:4]), int(next_month[4:]), 1)
    return start, end


def _file_meta() -> dict[str, Any]:
    data = DATA_PATH.read_bytes()
    return {
        "file": str(DATA_PATH),
        "file_hash": hashlib.sha256(data).hexdigest(),
        "file_size": len(data),
    }


def _read_map_rows() -> list[dict[str, str]]:
    with DATA_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError("rent_deal_ldong_adong_map.csv is empty")
    if set(rows[0]) != {"ldong_code", "adong_code"}:
        raise RuntimeError("rent_deal_ldong_adong_map.csv must have ldong_code,adong_code columns")
    ldong_codes = [row["ldong_code"] for row in rows]
    if any(not code for code in ldong_codes) or len(ldong_codes) != len(set(ldong_codes)):
        raise RuntimeError("rent_deal_ldong_adong_map.csv has blank or duplicate ldong_code")
    if len(rows) < 400:
        raise RuntimeError(f"refusing incomplete rent deal map: {len(rows)} rows")
    return rows


def _load_map(options: RentDealsUpdateOptions, meta: dict[str, Any]) -> dict[str, Any]:
    rows = _read_map_rows()
    previous_hash = dataset_state("rent_deals").get("map_snapshot", {}).get("file_hash")
    skipped_write = bool(previous_hash == meta["file_hash"] and not options.force and not options.dry_run)
    checked = len(rows)
    loaded = 0
    null_adong = 0

    if not skipped_write and not options.dry_run:
        ldong_ids = set(Ldong.objects.values_list("ldong_code", flat=True))
        adong_ids = set(Adong.objects.values_list("adong_code", flat=True))
        with transaction.atomic():
            for row in rows:
                ldong_id = row["ldong_code"]
                if ldong_id not in ldong_ids:
                    raise RuntimeError(f"rent deal map has unknown ldong_code={ldong_id}")
                adong_id = row.get("adong_code") or None
                if adong_id and adong_id not in adong_ids:
                    adong_id = None
                if not adong_id:
                    null_adong += 1
                RentDealLdongAdongMap.objects.update_or_create(
                    ldong_id=ldong_id,
                    defaults={"adong_id": adong_id},
                )
                loaded += 1
    else:
        null_adong = sum(1 for row in rows if not row.get("adong_code"))

    return {
        "status": "success",
        "completed": True,
        "checked": checked,
        "loaded": loaded,
        "null_adong": null_adong,
        "skipped_write": skipped_write,
        "files": meta,
    }


def _get(row: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _to_int(value: Any, *, required: bool = False) -> int | None:
    if value in (None, ""):
        if required:
            raise ValueError("missing integer value")
        return None
    text = str(value).replace(",", "").strip()
    if not text:
        if required:
            raise ValueError("missing integer value")
        return None
    return int(Decimal(text))


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    text = str(value).replace(",", "").strip()
    return Decimal(text) if text else None


def _contract_date(row: dict[str, str]) -> date:
    year = _get(row, "년", "dealYear")
    month = _get(row, "월", "dealMonth")
    day = _get(row, "일", "dealDay")
    if not (year and month and day):
        raise ValueError("missing contract date")
    return date(int(year), int(month), int(day))


def _rent_id(housing_type: str, lawd: str, ym: str, row: dict[str, str]) -> str:
    raw = "|".join([housing_type, lawd, ym, *(f"{key}={row.get(key)}" for key in sorted(row))])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:40]


def _xml_items(root: ET.Element) -> tuple[int, list[dict[str, str]], str | None]:
    result_code = (root.findtext("./header/resultCode") or "").strip() or None
    total_text = (root.findtext("./body/totalCount") or "0").strip()
    try:
        total = int(total_text)
    except ValueError:
        total = 0
    rows = []
    for item in root.findall(".//item"):
        row = {}
        for child in list(item):
            row[child.tag] = child.text.strip() if child.text else ""
        rows.append(row)
    return total, rows, result_code


def _request_xml(path: str, params: dict[str, str], options: RentDealsUpdateOptions) -> ET.Element:
    if options.request_interval_seconds:
        sleep_time.sleep(options.request_interval_seconds)
    query = urlencode(params, safe="%")
    url = f"{PUBLIC_DATA_BASE_URL}{path}?{query}"
    req = Request(url, headers={"User-Agent": "capston-public-data-updater/0.1"})
    try:
        with urlopen(req, timeout=options.request_timeout_seconds) as res:
            return ET.fromstring(res.read())
    except HTTPError as exc:
        if exc.code == 429:
            raise RateLimitedError(f"rent deal API rate limited: HTTP 429: {path}") from exc
        raise RuntimeError(f"rent deal API request failed: HTTP {exc.code}: {path}") from exc
    except (URLError, TimeoutError, socket.timeout) as exc:
        raise RuntimeError(f"rent deal API request failed: {type(exc).__name__}: {path}") from exc
    except ET.ParseError as exc:
        raise RuntimeError(f"rent deal API returned malformed XML: {path}") from exc


def _fetch_rows(
    *,
    api_key: str,
    path: str,
    lawd: str,
    ym: str,
    options: RentDealsUpdateOptions,
) -> list[dict[str, str]]:
    page = 1
    collected: list[dict[str, str]] = []
    while True:
        root = _request_xml(
            path,
            {
                "serviceKey": api_key,
                "LAWD_CD": lawd,
                "DEAL_YMD": ym,
                "pageNo": str(page),
                "numOfRows": str(PAGE_SIZE),
            },
            options,
        )
        total, rows, result_code = _xml_items(root)
        if result_code and result_code not in {"000", "00"}:
            if is_rate_limited_code(result_code) or is_rate_limited_text(result_code):
                raise RateLimitedError(
                    f"rent deal API rate limited resultCode={result_code} lawd={lawd} ym={ym}"
                )
            raise RuntimeError(f"rent deal API error resultCode={result_code} lawd={lawd} ym={ym}")
        collected.extend(rows)
        if not rows or not total or page * PAGE_SIZE >= total:
            return collected
        page += 1


def _resolve_ldong(lawd: str, row: dict[str, str], name_lookup: dict[tuple[str, str], str]) -> str | None:
    code = str(_get(row, "법정동시군구코드", "sggCd") or "") + str(_get(row, "법정동읍면동코드", "umdCd") or "")
    if len(code) == 10:
        return code
    name = str(_get(row, "법정동", "umdNm") or "").strip()
    if name:
        return name_lookup.get((lawd, name))
    return None


def _vworld_point(payload: dict[str, Any]) -> Point | None:
    items = payload.get("response", {}).get("result", {}).get("items", [])
    if not items:
        return None
    point = items[0].get("point") or {}
    try:
        return Point(float(point["x"]), float(point["y"]), srid=4326)
    except (KeyError, TypeError, ValueError):
        return None


def _request_json(url: str, params: dict[str, str], options: RentDealsUpdateOptions) -> Any:
    if options.request_interval_seconds:
        sleep_time.sleep(options.request_interval_seconds)
    req = Request(f"{url}?{urlencode(params, safe='%')}", headers={"User-Agent": "capston-public-data-updater/0.1"})
    try:
        with urlopen(req, timeout=options.request_timeout_seconds) as res:
            return json.loads(res.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, TimeoutError, socket.timeout, json.JSONDecodeError):
        return {}


def _geocode_location(
    *,
    vworld_key: str | None,
    ldong: Ldong,
    jibun: str | None,
    options: RentDealsUpdateOptions,
    cache: dict[str, tuple[Point | None, str | None]],
) -> tuple[Point | None, str | None]:
    if not vworld_key or not jibun:
        return None, None
    query = f"서울특별시 {ldong.gu.name} {ldong.name} {jibun}".strip()
    if query in cache:
        return cache[query]
    payload = _request_json(
        V_WORLD_GEOCODE_URL,
        {
            "service": "address",
            "request": "getCoord",
            "version": "2.0",
            "crs": "EPSG:4326",
            "address": query,
            "refine": "true",
            "simple": "false",
            "format": "json",
            "type": "PARCEL",
            "key": vworld_key,
        },
        options,
    )
    point = _vworld_point(payload)
    adong_id = None
    if point:
        adong = Adong.objects.filter(boundary__covers=point).order_by("area_m2").first()
        adong_id = adong.adong_code if adong else None
    cache[query] = (point, adong_id)
    return cache[query]


def _missing_months(months: list[str], current_ym: str) -> list[str]:
    missing = []
    for ym in months:
        if ym == current_ym:
            continue
        start, end = _month_bounds(ym)
        if not RentDeal.objects.filter(contract_date__gte=start, contract_date__lt=end).exists():
            missing.append(ym)
    return missing


def _build_deal(
    *,
    row: dict[str, str],
    housing_type: str,
    lawd: str,
    ym: str,
    ldong_by_id: dict[str, Ldong],
    ldong_name_lookup: dict[tuple[str, str], str],
    map_by_ldong: dict[str, str | None],
    vworld_key: str | None,
    options: RentDealsUpdateOptions,
    geocode_cache: dict[str, tuple[Point | None, str | None]],
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        contract_date = _contract_date(row)
    except (TypeError, ValueError):
        return None, "missing_contract_date"
    ldong_id = _resolve_ldong(lawd, row, ldong_name_lookup)
    ldong = ldong_by_id.get(ldong_id or "")
    if not ldong:
        return None, "unresolved_ldong"
    try:
        deposit = _to_int(_get(row, "보증금액", "deposit"), required=True)
        monthly_rent = _to_int(_get(row, "월세금액", "monthlyRent"), required=True)
    except (InvalidOperation, ValueError):
        return None, "bad_required_money"

    jibun = str(_get(row, "지번", "jibun") or "").strip()[:50] or None
    adong_id = map_by_ldong.get(ldong.ldong_code)
    location = None
    geocoded = False
    if jibun:
        location, geocoded_adong_id = _geocode_location(
            vworld_key=vworld_key,
            ldong=ldong,
            jibun=jibun,
            options=options,
            cache=geocode_cache,
        )
        geocoded = bool(location)
        if not adong_id:
            adong_id = geocoded_adong_id

    return (
        {
            "id": _rent_id(housing_type, lawd, ym, row),
            "defaults": {
                "housing_type": housing_type,
                "contract_date": contract_date,
                "contract_end_date": None,
                "contract_type": str(_get(row, "계약구분", "contractType") or "")[:20] or None,
                "renewal_request_right_used": None,
                "area_m2": _to_decimal(_get(row, "전용면적", "건물면적", "excluUseAr", "totalFloorAr")),
                "deposit": deposit,
                "monthly_rent": monthly_rent,
                "previous_deposit": _to_int(_get(row, "종전계약보증금", "previousDeposit")),
                "previous_monthly_rent": _to_int(_get(row, "종전계약월세", "previousMonthlyRent")),
                "floor": _to_int(_get(row, "층", "floor")),
                "construction_year": _to_int(_get(row, "건축년도", "buildYear")),
                "house_name": str(_get(row, "아파트", "단지", "aptNm", "houseNm", "offiNm", "mhouseNm") or "")[:100] or None,
                "jibun": jibun,
                "location": location,
                "ldong_id": ldong.ldong_code,
                "adong_id": adong_id,
            },
            "geocoded": geocoded,
        },
        None,
    )


def _fetch_month_deals(
    *,
    ym: str,
    api_key: str,
    vworld_key: str | None,
    lawds: list[str],
    ldong_by_id: dict[str, Ldong],
    ldong_name_lookup: dict[tuple[str, str], str],
    map_by_ldong: dict[str, str | None],
    options: RentDealsUpdateOptions,
    checked_start: int,
) -> dict[str, Any]:
    checked = skipped = geocoded = 0
    records: list[dict[str, Any]] = []
    skip_reasons = {
        "missing_contract_date": 0,
        "bad_required_money": 0,
        "unresolved_ldong": 0,
    }
    geocode_cache: dict[str, tuple[Point | None, str | None]] = {}

    for lawd in lawds:
        for housing_type, path in RENT_ENDPOINTS.items():
            rows = _fetch_rows(api_key=api_key, path=path, lawd=lawd, ym=ym, options=options)
            for row in rows:
                if options.limit is not None and checked_start + checked >= options.limit:
                    return {
                        "status": "partial",
                        "completed": False,
                        "ym": ym,
                        "checked": checked,
                        "records": records,
                        "skipped": skipped,
                        "skip_reasons": skip_reasons,
                        "geocoded": geocoded,
                    }
                checked += 1
                record, reason = _build_deal(
                    row=row,
                    housing_type=housing_type,
                    lawd=lawd,
                    ym=ym,
                    ldong_by_id=ldong_by_id,
                    ldong_name_lookup=ldong_name_lookup,
                    map_by_ldong=map_by_ldong,
                    vworld_key=vworld_key,
                    options=options,
                    geocode_cache=geocode_cache,
                )
                if not record:
                    skipped += 1
                    if reason:
                        skip_reasons[reason] += 1
                    continue
                if record.pop("geocoded"):
                    geocoded += 1
                records.append(record)

    return {
        "status": "success",
        "completed": True,
        "ym": ym,
        "checked": checked,
        "records": records,
        "skipped": skipped,
        "skip_reasons": skip_reasons,
        "geocoded": geocoded,
    }


def _upsert_records(records: list[dict[str, Any]]) -> dict[str, int]:
    loaded = created = updated = 0
    for record in records:
        _, was_created = RentDeal.objects.update_or_create(
            id=record["id"],
            defaults=record["defaults"],
        )
        loaded += 1
        created += int(was_created)
        updated += int(not was_created)
    return {"loaded": loaded, "created": created, "updated": updated}


def update_rent_deals(options: RentDealsUpdateOptions) -> dict[str, Any]:
    map_meta = _file_meta()
    mapping = _load_map(options, map_meta)
    start_ym = _validate_ym(options.start_ym or DEFAULT_START_YM)
    end_ym = _validate_ym(options.end_ym or _current_ym())
    current = _current_ym()
    months = _iter_months(start_ym, end_ym)
    missing = _missing_months(months, current)
    target_months = sorted(
        set(missing + ([current] if start_ym <= current <= end_ym else [])),
        reverse=True,
    )

    if not target_months:
        return {
            "status": "success",
            "completed": True,
            "loaded": mapping["loaded"],
            "dry_run": options.dry_run,
            "map": mapping,
            "rent_deals": {
                "checked": 0,
                "loaded": 0,
                "created": 0,
                "updated": 0,
                "deleted_current_month": 0,
                "missing_months": missing,
                "target_months": [],
                "months": {},
                "skipped_write": True,
                "reason": "no_missing_months",
            },
        }

    api_key = _require_env("PUBLIC_DATA_API_KEY")
    vworld_key = _optional_env("V_WORLD_API_KEY")
    ldongs = list(Ldong.objects.select_related("gu").all())
    ldong_by_id = {ldong.ldong_code: ldong for ldong in ldongs}
    ldong_name_lookup = {(ldong.gu_id, ldong.name): ldong.ldong_code for ldong in ldongs}
    lawds = sorted({ldong.gu_id for ldong in ldongs})
    map_by_ldong = {m.ldong_id: m.adong_id for m in RentDealLdongAdongMap.objects.all()}

    checked_total = loaded_total = created_total = updated_total = skipped_total = geocoded_total = 0
    deleted_current_month = 0
    month_results: dict[str, Any] = {}
    completed = True

    for ym in target_months:
        try:
            fetched = _fetch_month_deals(
                ym=ym,
                api_key=api_key,
                vworld_key=vworld_key,
                lawds=lawds,
                ldong_by_id=ldong_by_id,
                ldong_name_lookup=ldong_name_lookup,
                map_by_ldong=map_by_ldong,
                options=options,
                checked_start=checked_total,
            )
        except RateLimitedError as exc:
            completed = False
            month_results[ym] = {
                "status": "rate_limited",
                "completed": False,
                "checked": 0,
                "loaded": 0,
                "skipped": 0,
                "skip_reasons": {},
                "geocoded": 0,
                "current_month_replace": False,
                "error": str(exc),
            }
            break
        checked_total += fetched["checked"]
        skipped_total += fetched["skipped"]
        geocoded_total += fetched["geocoded"]
        if not fetched["completed"]:
            completed = False

        write_stats = {"loaded": 0, "created": 0, "updated": 0}
        if not options.dry_run:
            if ym == current and options.limit is None and fetched["completed"]:
                start, end = _month_bounds(ym)
                with transaction.atomic():
                    current_qs = RentDeal.objects.filter(contract_date__gte=start, contract_date__lt=end)
                    deleted_current_month = current_qs.count()
                    current_qs.delete()
                    write_stats = _upsert_records(fetched["records"])
            elif ym != current and fetched["completed"]:
                with transaction.atomic():
                    write_stats = _upsert_records(fetched["records"])
            else:
                completed = False

        loaded_total += write_stats["loaded"]
        created_total += write_stats["created"]
        updated_total += write_stats["updated"]
        month_results[ym] = {
            "status": fetched["status"] if fetched["completed"] else "partial",
            "completed": fetched["completed"],
            "checked": fetched["checked"],
            "loaded": write_stats["loaded"] if not options.dry_run else len(fetched["records"]),
            "skipped": fetched["skipped"],
            "skip_reasons": fetched["skip_reasons"],
            "geocoded": fetched["geocoded"],
            "current_month_replace": ym == current and options.limit is None,
        }
        if not fetched["completed"]:
            break

    after_missing = _missing_months(months, current) if not options.dry_run else missing
    if after_missing:
        completed = False

    rent_deals = {
        "status": "success" if completed else "partial",
        "completed": completed,
        "checked": checked_total,
        "loaded": loaded_total,
        "created": created_total,
        "updated": updated_total,
        "skipped": skipped_total,
        "geocoded": geocoded_total,
        "deleted_current_month": deleted_current_month,
        "missing_months": missing,
        "after_missing_months": after_missing,
        "target_months": target_months,
        "months": month_results,
        "loaded_start": min(month_results) if month_results else None,
        "loaded_end": max(month_results) if month_results else None,
        "vworld_enabled": bool(vworld_key),
    }
    return {
        "status": "success" if completed else "partial",
        "completed": completed,
        "loaded": mapping["loaded"] + loaded_total,
        "dry_run": options.dry_run,
        "map": mapping,
        "rent_deals": rent_deals,
    }


def update(options: RentDealsUpdateOptions) -> dict[str, Any]:
    result: dict[str, Any] = {
        "dataset": "rent_deals",
        "dry_run": options.dry_run,
        "rent_deals": None,
    }
    try:
        result["rent_deals"] = update_rent_deals(options)
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if not options.dry_run:
            record_dataset_result("rent_deals", result)
        raise

    if not options.dry_run:
        record_dataset_result("rent_deals", result)
        if result["rent_deals"] and result["rent_deals"].get("completed"):
            state = load_state()
            rent_state = state.setdefault("datasets", {}).setdefault("rent_deals", {})
            rent_state["map_snapshot"] = result["rent_deals"]["map"]["files"] | {
                "loaded": result["rent_deals"]["map"]["loaded"],
                "null_adong": result["rent_deals"]["map"]["null_adong"],
            }
            rent_state["rent_deals"] = {
                "last_success_month": result["rent_deals"]["rent_deals"].get("loaded_end"),
                "loaded_start": result["rent_deals"]["rent_deals"].get("loaded_start"),
                "loaded_end": result["rent_deals"]["rent_deals"].get("loaded_end"),
                "missing_months": result["rent_deals"]["rent_deals"].get("after_missing_months"),
                "deleted_current_month": result["rent_deals"]["rent_deals"].get("deleted_current_month"),
            }
            save_state(state)
    return result
