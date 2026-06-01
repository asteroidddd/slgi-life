
"""Medical public-data updater for Seoul hospitals, pharmacies, emergency, and holiday care."""

from __future__ import annotations

import json
import math
import os
import re
import socket
import time as sleep_time
import xml.etree.ElementTree as ET
import csv
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.contrib.gis.geos import Point
from django.db import transaction

from apps.public_data.api_keys import env_key_ring, with_rate_limit_fallback
from apps.public_data.exceptions import RateLimitedError, is_rate_limited_code, is_rate_limited_text
from apps.public_data.medical.models import (
    MedicalEmergency,
    MedicalFacility,
    MedicalFacilityHours,
    MedicalFacilitySpecialty,
    MedicalHiraMapping,
    MedicalHolidayCare,
)
from apps.public_data.regions.models import Adong, Ldong
from apps.public_data.state import record_dataset_result
from apps.common.geocoding import geocode_address as _shared_geocode_address


HOSPITAL_API_URL = "https://apis.data.go.kr/B552657/HsptlAsembySearchService/getHsptlMdcncListInfoInqire"
PHARMACY_API_URL = "https://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyListInfoInqire"
EMERGENCY_API_URL = "https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEgytListInfoInqire"
HOLIDAY_API_URL = "https://apis.data.go.kr/B552657/HolidyEmgncClnicInsttInfoInqireService/getHolidyClnicPosblEgytInfoInqire"
HIRA_HOSPITAL_API_URL = "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
HIRA_SPECIALTY_API_URL = "https://apis.data.go.kr/B551182/MadmDtlInfoService2.7/getDgsbjtInfo2.7"
PAGE_SIZE = 1000
SEOUL_Q0 = "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc"
HIRA_MATCH_EXCLUDED_TYPES = {
    "\uc57d\uad6d",
    "\uc694\uc591\ubcd1\uc6d0",
    "\uc870\uc0b0\uc6d0",
    "\uae30\ud0c0",
    "\uae30\ud0c0(\uad6c\uae09\ucc28)",
}
SPECIALTY_GROUPS_PATH = Path(__file__).resolve().parents[3] / "data" / "medical_specialty_groups.csv"


DAY_FIELDS = (
    ("mon", "dutyTime1s", "dutyTime1c"),
    ("tue", "dutyTime2s", "dutyTime2c"),
    ("wed", "dutyTime3s", "dutyTime3c"),
    ("thu", "dutyTime4s", "dutyTime4c"),
    ("fri", "dutyTime5s", "dutyTime5c"),
    ("sat", "dutyTime6s", "dutyTime6c"),
    ("sun", "dutyTime7s", "dutyTime7c"),
    ("holiday", "dutyTime8s", "dutyTime8c"),
)


@dataclass(frozen=True)
class MedicalUpdateOptions:
    dry_run: bool = True
    force: bool = False
    limit: int | None = None
    request_interval_seconds: float = 0.2
    request_timeout_seconds: float = 40.0
    geocode_missing: bool = True
    update_hira_specialties: bool = False


def _text(value: Any, limit: int | None = None) -> str:
    text = str(value or "").strip()
    return text[:limit] if limit else text


@lru_cache(maxsize=1)
def _specialty_group_by_name() -> dict[str, str]:
    try:
        with SPECIALTY_GROUPS_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            return {
                (row.get("specialty_name") or "").strip(): (row.get("specialty_group") or "").strip()
                for row in csv.DictReader(handle)
                if (row.get("specialty_name") or "").strip() and (row.get("specialty_group") or "").strip()
            }
    except FileNotFoundError:
        return {}


def _specialty_group(name: str) -> str:
    return _specialty_group_by_name().get(name, "기타")


def _request_xml(url: str, params: dict[str, str], options: MedicalUpdateOptions) -> ET.Element:
    if options.request_interval_seconds:
        sleep_time.sleep(options.request_interval_seconds)
    req = Request(
        f"{url}?{urlencode(params, safe='%')}",
        headers={"User-Agent": "capston-medical-data-updater/0.1"},
    )
    try:
        with urlopen(req, timeout=options.request_timeout_seconds) as res:
            return ET.fromstring(res.read())
    except HTTPError as exc:
        if exc.code == 429:
            raise RateLimitedError(f"medical API rate limited: HTTP {exc.code}") from exc
        raise RuntimeError(f"medical API request failed: HTTP {exc.code}") from exc
    except (URLError, TimeoutError, socket.timeout) as exc:
        raise RuntimeError(f"medical API request failed: {type(exc).__name__}") from exc
    except ET.ParseError as exc:
        raise RuntimeError("medical API returned malformed XML") from exc


def _element_text(element: ET.Element, name: str) -> str:
    found = element.find(name)
    return _text(found.text if found is not None else "")


def _response_items(root: ET.Element, *, dataset: str) -> tuple[int, list[dict[str, str]]]:
    code = _element_text(root, "./header/resultCode")
    msg = _element_text(root, "./header/resultMsg")
    if code and code not in {"00", "NORMAL SERVICE."}:
        if is_rate_limited_code(code) or is_rate_limited_text({"resultMsg": msg}):
            raise RateLimitedError(f"{dataset} API rate limited resultCode={code} resultMsg={msg}")
        raise RuntimeError(f"{dataset} API error resultCode={code} resultMsg={msg}")
    total_text = _element_text(root, "./body/totalCount")
    total = int(total_text or 0)
    rows: list[dict[str, str]] = []
    for item in root.findall("./body/items/item"):
        rows.append({child.tag: _text(child.text) for child in list(item)})
    return total, rows


def _fetch_pages(api_key: str, url: str, dataset: str, options: MedicalUpdateOptions) -> list[dict[str, str]]:
    page = 1
    out: list[dict[str, str]] = []
    while True:
        root = _request_xml(
            url,
            {
                "serviceKey": api_key,
                "Q0": SEOUL_Q0,
                "pageNo": str(page),
                "numOfRows": str(PAGE_SIZE),
                "ORD": "NAME",
            },
            options,
        )
        total, rows = _response_items(root, dataset=dataset)
        out.extend(rows)
        if not rows or not total or page * PAGE_SIZE >= total:
            return out
        if options.limit is not None and len(out) >= options.limit:
            return out[: options.limit]
        page += 1


def _fetch_pages_with_fallback(url: str, dataset: str, options: MedicalUpdateOptions) -> list[dict[str, str]]:
    keys = env_key_ring("PUBLIC_DATA_API_KEY")
    return with_rate_limit_fallback(keys, lambda api_key: _fetch_pages(api_key, url, dataset, options))


def _parse_time(value: Any) -> time | None:
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not text:
        return None
    text = text.zfill(4)[-4:]
    hour = int(text[:2])
    minute = int(text[2:])
    if hour == 24 and minute == 0:
        return time(23, 59)
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def _point(row: dict[str, Any]) -> Point | None:
    lon = row.get("wgs84Lon") or row.get("lon") or row.get("longitude")
    lat = row.get("wgs84Lat") or row.get("lat") or row.get("latitude")
    try:
        return Point(float(lon), float(lat), srid=4326)
    except (TypeError, ValueError):
        return None


def _geocode_address(address: str, options: MedicalUpdateOptions) -> Point | None:
    if not (options.geocode_missing and address):
        return None
    result = _shared_geocode_address(
        address,
        request_timeout=options.request_timeout_seconds,
        request_interval=options.request_interval_seconds,
        user_agent="capston-medical-data-updater/0.1",
    )
    return result.point if result.status == "success" else None


def _find_region(point: Point) -> tuple[Ldong | None, Adong | None]:
    ldong = Ldong.objects.filter(boundary__covers=point).order_by("area_m2").first()
    adong = Adong.objects.filter(boundary__covers=point).order_by("area_m2").first()
    return ldong, adong


def _facility_defaults(row: dict[str, str], *, facility_type: str, options: MedicalUpdateOptions) -> tuple[dict[str, Any] | None, str]:
    address = _text(row.get("dutyAddr"), 255)
    point = _point(row) or _geocode_address(address, options)
    if not point:
        return None, "missing_location"
    ldong, adong = _find_region(point)
    if not (ldong and adong):
        return None, "region_not_found"
    return (
        {
            "type": facility_type[:30],
            "name": _text(row.get("dutyName"), 200),
            "address": address,
            "location": point,
            "adong_id": adong.adong_code,
            "ldong_id": ldong.ldong_code,
            "tel1": _text(row.get("dutyTel1"), 30),
            "note": _text(row.get("dutyEtc")),
        },
        "",
    )


def _hour_rows(row: dict[str, str], hpid: str) -> list[MedicalFacilityHours]:
    rows: list[MedicalFacilityHours] = []
    for day_type, open_field, close_field in DAY_FIELDS:
        open_time = _parse_time(row.get(open_field))
        close_time = _parse_time(row.get(close_field))
        rows.append(
            MedicalFacilityHours(
                facility_id=hpid,
                day_type=day_type,
                open_time=open_time,
                close_time=close_time,
                is_closed=not (open_time and close_time),
            )
        )
    return rows


def _build_facility_rows(rows: list[dict[str, str]], *, source: str, options: MedicalUpdateOptions) -> dict[str, Any]:
    records: list[tuple[str, dict[str, Any]]] = []
    hour_rows: list[MedicalFacilityHours] = []
    checked = skipped = 0
    skip_reasons = {"missing_hpid": 0, "missing_location": 0, "region_not_found": 0, "missing_type": 0}

    for row in rows:
        checked += 1
        hpid = _text(row.get("hpid"), 30)
        if not hpid:
            skipped += 1
            skip_reasons["missing_hpid"] += 1
            continue
        facility_type = "\uc57d\uad6d" if source == "pharmacy" else _text(row.get("dutyDivNam"), 30)
        if not facility_type:
            skipped += 1
            skip_reasons["missing_type"] += 1
            continue
        defaults, reason = _facility_defaults(row, facility_type=facility_type, options=options)
        if not defaults:
            skipped += 1
            skip_reasons[reason] += 1
            continue
        records.append((hpid, defaults))
        hour_rows.extend(_hour_rows(row, hpid))
    return {"checked": checked, "records": records, "hours": hour_rows, "skipped": skipped, "skip_reasons": skip_reasons}


def _update_facilities(options: MedicalUpdateOptions) -> dict[str, Any]:
    hospital_rows = _fetch_pages_with_fallback(HOSPITAL_API_URL, "hospital", options)
    pharmacy_rows = _fetch_pages_with_fallback(PHARMACY_API_URL, "pharmacy", options)
    hospital = _build_facility_rows(hospital_rows, source="hospital", options=options)
    pharmacy = _build_facility_rows(pharmacy_rows, source="pharmacy", options=options)
    all_records = hospital["records"] + pharmacy["records"]
    all_hours = hospital["hours"] + pharmacy["hours"]

    loaded = created = updated = hours_loaded = deleted_missing = 0
    if options.dry_run:
        loaded = len(all_records)
        hours_loaded = len(all_hours)
    else:
        records_by_hpid = {hpid: defaults for hpid, defaults in all_records}
        hpids = list(records_by_hpid)
        existing_hpids = set(MedicalFacility.objects.filter(hpid__in=hpids).values_list("hpid", flat=True))
        with transaction.atomic():
            MedicalFacility.objects.bulk_create(
                [
                    MedicalFacility(hpid=hpid, **defaults)
                    for hpid, defaults in records_by_hpid.items()
                ],
                batch_size=2000,
                update_conflicts=True,
                update_fields=[
                    "type",
                    "name",
                    "address",
                    "location",
                    "adong",
                    "ldong",
                    "tel1",
                    "note",
                ],
                unique_fields=["hpid"],
            )
            loaded = len(records_by_hpid)
            created = len(set(hpids) - existing_hpids)
            updated = len(set(hpids) & existing_hpids)
            if options.limit is None:
                stale_qs = MedicalFacility.objects.exclude(hpid__in=hpids)
                deleted_missing = stale_qs.count()
                stale_qs.delete()
            MedicalFacilityHours.objects.filter(facility_id__in=hpids).delete()
            MedicalFacilityHours.objects.bulk_create(all_hours, batch_size=2000)
            hours_loaded = len(all_hours)
    return {
        "status": "success",
        "completed": True,
        "dry_run": options.dry_run,
        "checked": {"hospital": hospital["checked"], "pharmacy": pharmacy["checked"]},
        "loaded": loaded,
        "created": created,
        "updated": updated,
        "hours_loaded": hours_loaded,
        "deleted_missing": deleted_missing,
        "skipped": {"hospital": hospital["skipped"], "pharmacy": pharmacy["skipped"]},
        "skip_reasons": {"hospital": hospital["skip_reasons"], "pharmacy": pharmacy["skip_reasons"]},
    }


def _update_emergency(options: MedicalUpdateOptions) -> dict[str, Any]:
    rows = _fetch_pages_with_fallback(EMERGENCY_API_URL, "emergency", options)
    existing_hpids = set(MedicalFacility.objects.values_list("hpid", flat=True))
    checked = loaded = skipped_missing_facility = 0
    if not options.dry_run:
        emergency_rows: list[MedicalEmergency] = []
        for row in rows:
            checked += 1
            hpid = _text(row.get("hpid"), 30)
            if hpid not in existing_hpids:
                skipped_missing_facility += 1
                continue
            emergency_rows.append(
                MedicalEmergency(
                    facility_id=hpid,
                    phpid=_text(row.get("phpid"), 30),
                    emergency_type=_text(row.get("dutyEmclsName") or row.get("dutyEmcls"), 100),
                    tel2=_text(row.get("dutyTel3"), 30),
                    has_emergency_room=True,
                    note=_text(row.get("dutyEtc")),
                )
            )
        with transaction.atomic():
            MedicalEmergency.objects.all().delete()
            MedicalEmergency.objects.bulk_create(emergency_rows, batch_size=2000)
            loaded = len(emergency_rows)
    else:
        for row in rows:
            checked += 1
            hpid = _text(row.get("hpid"), 30)
            if hpid in existing_hpids:
                loaded += 1
            else:
                skipped_missing_facility += 1
    return {
        "status": "success",
        "completed": True,
        "dry_run": options.dry_run,
        "checked": checked,
        "loaded": loaded,
        "skipped_missing_facility": skipped_missing_facility,
    }


def _parse_date(value: Any) -> date | None:
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(text) != 8:
        return None
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return None


def _parse_time_range(value: Any) -> tuple[time | None, time | None, bool]:
    text = str(value or "").strip()
    if not text:
        return None, None, True
    digits = "".join(ch if ch.isdigit() else " " for ch in text).split()
    if len(digits) >= 2:
        return _parse_time(digits[0]), _parse_time(digits[1]), False
    if len(digits) == 1 and len(digits[0]) >= 8:
        return _parse_time(digits[0][:4]), _parse_time(digits[0][4:8]), False
    return None, None, False


def _update_holiday(options: MedicalUpdateOptions) -> dict[str, Any]:
    rows = _fetch_pages_with_fallback(HOLIDAY_API_URL, "holiday", options)
    existing_hpids = set(MedicalFacility.objects.values_list("hpid", flat=True))
    today = date.today()
    care_rows: list[MedicalHolidayCare] = []
    checked = skipped_past = skipped_missing_facility = 0

    for row in rows:
        checked += 1
        hpid = _text(row.get("hpid"), 30)
        if hpid not in existing_hpids:
            skipped_missing_facility += 1
            continue
        for index in range(1, 6):
            care_date = _parse_date(row.get(f"dutyDay{index}"))
            if not care_date:
                continue
            if care_date < today:
                skipped_past += 1
                continue
            open_time, close_time, is_closed = _parse_time_range(row.get(f"dutyDaytime{index}"))
            care_rows.append(
                MedicalHolidayCare(
                    facility_id=hpid,
                    care_date=care_date,
                    open_time=open_time,
                    close_time=close_time,
                    is_closed=is_closed,
                    note=_text(row.get("dutyDayetc")),
                )
            )
    if not options.dry_run:
        with transaction.atomic():
            MedicalHolidayCare.objects.all().delete()
            MedicalHolidayCare.objects.bulk_create(care_rows, batch_size=2000, ignore_conflicts=True)
    return {
        "status": "success",
        "completed": True,
        "dry_run": options.dry_run,
        "checked": checked,
        "loaded": len(care_rows),
        "skipped_past_dates": skipped_past,
        "skipped_missing_facility": skipped_missing_facility,
        "future_dates": sorted({item.care_date.isoformat() for item in care_rows}),
    }


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _normalize_name(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[\(\)\[\]{},.-]", "", text).replace("\u00b7", "").replace("\u318d", "")
    for token in (
        "\uc758\ub8cc\ubc95\uc778",
        "\uc0ac\ud68c\ubcf5\uc9c0\ubc95\uc778",
        "\uc7ac\ub2e8\ubc95\uc778",
        "\ud559\uad50\ubc95\uc778",
    ):
        text = text.replace(token, "")
    return text


def _normalize_address(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("\uc11c\uc6b8\ud2b9\ubcc4\uc2dc", "\uc11c\uc6b8").replace("\uc11c\uc6b8\uc2dc", "\uc11c\uc6b8")
    return re.sub(r"[,.-]", "", text)


def _haversine_m(lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius_m = 6371000
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    d_phi = math.radians(float(lat2) - float(lat1))
    d_lambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _request_json_or_xml(url: str, params: dict[str, str], options: MedicalUpdateOptions) -> tuple[int | None, list[dict[str, Any]]]:
    encoded_url = f"{url}?{urlencode(params, safe='%')}"
    last_error: Exception | None = None
    for attempt in range(3):
        if options.request_interval_seconds:
            sleep_time.sleep(options.request_interval_seconds)
        req = Request(
            encoded_url,
            headers={"User-Agent": "capston-medical-data-updater/0.1"},
        )
        try:
            with urlopen(req, timeout=options.request_timeout_seconds) as res:
                body = res.read()
        except HTTPError as exc:
            if exc.code == 429 or exc.code == 403:
                raise RateLimitedError(f"HIRA API rate limited or rejected: HTTP {exc.code}") from exc
            if exc.code == 504 or exc.code == 503 or exc.code == 502:
                last_error = exc
                sleep_time.sleep(1 + attempt)
                continue
            raise
        except (URLError, socket.timeout) as exc:
            last_error = exc
            sleep_time.sleep(1 + attempt)
            continue

        try:
            payload = json.loads(body.decode("utf-8"))
            items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            total = payload.get("response", {}).get("body", {}).get("totalCount")
            if isinstance(items, dict):
                items = [items]
            return int(total) if total not in (None, "") else None, list(items or [])
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError, ValueError):
            root = ET.fromstring(body)
            result_code = root.findtext(".//resultCode", "")
            result_msg = root.findtext(".//resultMsg", "")
            if is_rate_limited_code(result_code) or is_rate_limited_text(result_msg):
                raise RateLimitedError(f"API rate limited: {result_code} {result_msg}".strip())
            total_text = root.findtext(".//totalCount")
            rows = [{child.tag: child.text for child in item} for item in root.findall(".//item")]
            return int(total_text) if total_text else None, rows
    if last_error:
        raise last_error
    return None, []


def _fetch_hira_hospitals(api_key: str, options: MedicalUpdateOptions) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        total, rows = _request_json_or_xml(
            HIRA_HOSPITAL_API_URL,
            {
                "serviceKey": api_key,
                "pageNo": str(page),
                "numOfRows": str(PAGE_SIZE),
                "sidoCd": "110000",
                "_type": "json",
            },
            options,
        )
        out.extend(rows)
        if not rows or not total or page * PAGE_SIZE >= total:
            return out
        page += 1


def _fetch_hira_hospitals_with_fallback(options: MedicalUpdateOptions) -> list[dict[str, Any]]:
    keys = env_key_ring("PUBLIC_DATA_API_KEY")
    return with_rate_limit_fallback(keys, lambda api_key: _fetch_hira_hospitals(api_key, options))


def _fetch_hira_specialties(api_key: str, ykiho: str, options: MedicalUpdateOptions) -> list[dict[str, Any]]:
    _total, rows = _request_json_or_xml(
        HIRA_SPECIALTY_API_URL,
        {
            "serviceKey": api_key,
            "ykiho": ykiho,
            "pageNo": "1",
            "numOfRows": "100",
            "_type": "json",
        },
        options,
    )
    return rows


def _fetch_hira_specialties_with_fallback(ykiho: str, options: MedicalUpdateOptions) -> list[dict[str, Any]]:
    keys = env_key_ring("PUBLIC_DATA_API_KEY")
    return with_rate_limit_fallback(keys, lambda api_key: _fetch_hira_specialties(api_key, ykiho, options))


HIRA_TYPE_COMPATIBILITY = {
    "\uc758\uc6d0": {"\uc758\uc6d0"},
    "\uce58\uacfc\uc758\uc6d0": {"\uce58\uacfc\uc758\uc6d0"},
    "\ud55c\uc758\uc6d0": {"\ud55c\uc758\uc6d0"},
    "\ubcd1\uc6d0": {"\ubcd1\uc6d0"},
    "\uc885\ud569\ubcd1\uc6d0": {"\uc885\ud569\ubcd1\uc6d0", "\uc0c1\uae09\uc885\ud569"},
    "\ud55c\ubc29\ubcd1\uc6d0": {"\ud55c\ubc29\ubcd1\uc6d0"},
    "\uce58\uacfc\ubcd1\uc6d0": {"\uce58\uacfc\ubcd1\uc6d0"},
    "\uc694\uc591\ubcd1\uc6d0": {"\uc694\uc591\ubcd1\uc6d0"},
    "\ubcf4\uac74\uc18c": {"\ubcf4\uac74\uc18c", "\ubcf4\uac74\uc9c0\uc18c", "\ubcf4\uac74\uc9c4\ub8cc\uc18c", "\ubcf4\uac74\uc758\ub8cc\uc6d0"},
    "\uc870\uc0b0\uc6d0": {"\uc870\uc0b0\uc6d0"},
}


def _hira_point(row: dict[str, Any]) -> tuple[float | None, float | None]:
    try:
        return float(row.get("YPos")), float(row.get("XPos"))
    except (TypeError, ValueError):
        return None, None


def _hira_item(row: dict[str, Any]) -> dict[str, Any]:
    lat, lon = _hira_point(row)
    name = _text(row.get("yadmNm"), 200)
    address = _text(row.get("addr"), 255)
    tel = _digits(row.get("telno"))
    return {
        "ykiho": _text(row.get("ykiho"), 120),
        "type": _text(row.get("clCdNm"), 40),
        "name": name,
        "address": address,
        "tel": tel,
        "lat": lat,
        "lon": lon,
        "name_norm": _normalize_name(name),
        "address_norm": _normalize_address(address),
    }


def _facility_match_item(facility: MedicalFacility) -> dict[str, Any]:
    return {
        "hpid": facility.hpid,
        "type": facility.type,
        "name": facility.name,
        "address": facility.address,
        "tel": _digits(facility.tel1),
        "lat": facility.location.y if facility.location else None,
        "lon": facility.location.x if facility.location else None,
        "name_norm": _normalize_name(facility.name),
        "address_norm": _normalize_address(facility.address),
    }


def _is_hira_type_compatible(facility_type: str, hira_type: str) -> bool:
    allowed = HIRA_TYPE_COMPATIBILITY.get(facility_type)
    return bool(allowed and hira_type in allowed)


def _safe_hira_candidates(facility: dict[str, Any], hira_rows: list[dict[str, Any]]) -> list[tuple[str, Decimal, dict[str, Any]]]:
    candidates: list[tuple[str, Decimal, dict[str, Any]]] = []
    for hira in hira_rows:
        if not hira["ykiho"] or not _is_hira_type_compatible(facility["type"], hira["type"]):
            continue
        if facility["name_norm"] != hira["name_norm"]:
            continue
        if facility["address_norm"] == hira["address_norm"]:
            candidates.append(("exact_name_address", Decimal("1.000"), hira))
            continue
        distance = _haversine_m(facility["lat"], facility["lon"], hira["lat"], hira["lon"])
        if distance is not None and distance <= 50:
            candidates.append(("exact_name_coord_50m", Decimal("0.950"), hira))
            continue
        if facility["tel"] and hira["tel"] and facility["tel"][-8:] == hira["tel"][-8:]:
            candidates.append(("exact_name_phone", Decimal("0.920"), hira))
    return candidates



def _select_safe_candidate(candidates: list[tuple[str, Decimal, dict[str, Any]]]) -> tuple[str, Decimal, dict[str, Any]] | None:
    for method in ("exact_name_address", "exact_name_coord_50m", "exact_name_phone"):
        method_candidates = [candidate for candidate in candidates if candidate[0] == method]
        if not method_candidates:
            continue
        by_ykiho: dict[str, tuple[str, Decimal, dict[str, Any]]] = {}
        for candidate in method_candidates:
            by_ykiho.setdefault(candidate[2]["ykiho"], candidate)
        if len(by_ykiho) == 1:
            return next(iter(by_ykiho.values()))
        return None
    return None

def _build_hira_matches(hira_rows: list[dict[str, Any]]) -> dict[str, Any]:
    hira_by_name: dict[str, list[dict[str, Any]]] = {}
    for row in hira_rows:
        item = _hira_item(row)
        if not item["name_norm"]:
            continue
        hira_by_name.setdefault(item["name_norm"], []).append(item)

    facilities = MedicalFacility.objects.exclude(type__in=HIRA_MATCH_EXCLUDED_TYPES).only("hpid", "type", "name", "address", "tel1", "location")
    matches: dict[str, tuple[str, Decimal, str]] = {}
    stats: dict[str, Any] = {
        "checked": 0,
        "matched": 0,
        "ambiguous": 0,
        "unmatched": 0,
        "method_counts": {},
        "unmatched_samples": [],
        "ambiguous_samples": [],
    }
    method_counts: dict[str, int] = {}

    for facility_obj in facilities.iterator(chunk_size=2000):
        stats["checked"] += 1
        facility = _facility_match_item(facility_obj)
        candidates = _safe_hira_candidates(facility, hira_by_name.get(facility["name_norm"], []))
        selected = _select_safe_candidate(candidates)
        if selected is not None:
            method, score, hira = selected
            matches[facility["hpid"]] = (hira["ykiho"], score, method)
            method_counts[method] = method_counts.get(method, 0) + 1
        elif candidates:
            stats["ambiguous"] += 1
            if len(stats["ambiguous_samples"]) < 20:
                stats["ambiguous_samples"].append(
                    {
                        "hpid": facility["hpid"],
                        "type": facility["type"],
                        "name": facility["name"],
                        "candidate_count": len(candidates),
                        "candidates": [
                            {"method": method, "hira_type": hira["type"], "name": hira["name"], "address": hira["address"]}
                            for method, _score, hira in candidates[:5]
                        ],
                    }
                )
        else:
            stats["unmatched"] += 1
            if len(stats["unmatched_samples"]) < 20:
                stats["unmatched_samples"].append(
                    {
                        "hpid": facility["hpid"],
                        "type": facility["type"],
                        "name": facility["name"],
                        "address": facility["address"],
                    }
                )

    stats["matched"] = len(matches)
    stats["method_counts"] = method_counts
    return {"matches": matches, "stats": stats}


def _hira_specialty_max_calls(options: MedicalUpdateOptions) -> int | None:
    if options.dry_run:
        return min(options.limit or 20, 100)
    raw = os.environ.get("MEDICAL_HIRA_SPECIALTY_MAX_CALLS", "9000").strip()
    if raw.lower() in ("", "0", "none", "all"):
        return None
    try:
        return max(1, int(raw))
    except ValueError:
        return 9000


def _specialty_rows_for_matches(
    matches: dict[str, tuple[str, Decimal, str]],
    options: MedicalUpdateOptions,
    *,
    specialty_limit: int | None = None,
) -> tuple[list[MedicalFacilitySpecialty], dict[str, Any]]:
    rows: list[MedicalFacilitySpecialty] = []
    checked = skipped_empty = failed = 0
    rate_limited = False
    fetched_facility_ids: set[str] = set()
    failed_samples: list[dict[str, str]] = []
    match_items = list(matches.items())
    if specialty_limit is not None:
        match_items = match_items[:specialty_limit]

    for hpid, (ykiho, _score, _method) in match_items:
        checked += 1
        try:
            specialties = _fetch_hira_specialties_with_fallback(ykiho, options)
        except RateLimitedError as exc:
            failed += 1
            rate_limited = True
            if len(failed_samples) < 20:
                failed_samples.append({"hpid": hpid, "error": f"{type(exc).__name__}: {exc}"})
            break
        except Exception as exc:
            failed += 1
            if len(failed_samples) < 20:
                failed_samples.append({"hpid": hpid, "error": f"{type(exc).__name__}: {exc}"})
            continue
        loaded_for_facility = 0
        seen: set[str] = set()
        fetched_facility_ids.add(hpid)
        for row in specialties:
            name = _text(row.get("dgsbjtCdNm"), 100)
            if not name or name in seen:
                continue
            seen.add(name)
            try:
                specialist_count = int(row.get("dgsbjtPrSdrCnt") or 0)
            except (TypeError, ValueError):
                specialist_count = 0
            rows.append(
                MedicalFacilitySpecialty(
                    mapping_id=ykiho,
                    specialty_name=name,
                    specialty_group=_specialty_group(name),
                    specialist_count=max(specialist_count, 0),
                )
            )
            loaded_for_facility += 1
        if loaded_for_facility == 0:
            skipped_empty += 1
    return rows, {
        "checked": checked,
        "failed": failed,
        "failed_samples": failed_samples,
        "empty": skipped_empty,
        "rate_limited": rate_limited,
        "fetched_facility_ids": sorted(fetched_facility_ids),
    }



def _eligible_hira_hpids() -> set[str]:
    return set(
        MedicalFacility.objects.exclude(type__in=HIRA_MATCH_EXCLUDED_TYPES).values_list("hpid", flat=True)
    )


def _mapping_pairs() -> dict[str, str]:
    return dict(MedicalHiraMapping.objects.values_list("facility_id", "hira_ykiho"))


def _update_hira_mapping(options: MedicalUpdateOptions) -> dict[str, Any]:
    eligible_hpids = _eligible_hira_hpids()
    existing_pairs = _mapping_pairs()
    existing_hpids = set(existing_pairs)
    needs_refresh = bool(options.force or eligible_hpids != existing_hpids)

    if not needs_refresh:
        return {
            "status": "skipped",
            "completed": True,
            "dry_run": options.dry_run,
            "reason": "facility_set_unchanged",
            "eligible_facility_count": len(eligible_hpids),
            "mapped_facility_count": len(existing_hpids),
            "new_facility_count": 0,
            "removed_facility_count": 0,
            "hira_rows": 0,
            "match": {
                "checked": len(eligible_hpids),
                "matched": len(existing_hpids),
                "ambiguous": 0,
                "unmatched": max(0, len(eligible_hpids) - len(existing_hpids)),
                "method_counts": {},
                "unmatched_samples": [],
                "ambiguous_samples": [],
            },
        }

    hira_rows = _fetch_hira_hospitals_with_fallback(options)
    match_result = _build_hira_matches(hira_rows)
    matches: dict[str, tuple[str, Decimal, str]] = match_result["matches"]

    if not options.dry_run:
        with transaction.atomic():
            MedicalHiraMapping.objects.all().delete()
            MedicalHiraMapping.objects.bulk_create(
                [
                    MedicalHiraMapping(facility_id=hpid, hira_ykiho=ykiho)
                    for hpid, (ykiho, _score, _method) in matches.items()
                ],
                batch_size=2000,
                ignore_conflicts=True,
            )

    return {
        "status": "success",
        "completed": True,
        "dry_run": options.dry_run,
        "reason": "forced" if options.force else "facility_set_changed",
        "eligible_facility_count": len(eligible_hpids),
        "mapped_facility_count": len(matches),
        "new_facility_count": len(eligible_hpids - existing_hpids),
        "removed_facility_count": len(existing_hpids - eligible_hpids),
        "hira_rows": len(hira_rows),
        "match": match_result["stats"],
    }


def _update_hira_specialties(options: MedicalUpdateOptions) -> dict[str, Any]:
    if not options.update_hira_specialties:
        return {"status": "skipped", "completed": True, "dry_run": options.dry_run, "reason": "disabled_by_option"}

    mapping_pairs = _mapping_pairs()
    if not mapping_pairs:
        return {
            "status": "skipped",
            "completed": True,
            "dry_run": options.dry_run,
            "reason": "no_hira_mapping",
            "specialty": {"checked": 0, "rows": 0},
        }

    existing_specialty_ykihos: set[str] = set()
    if not options.dry_run and not options.force:
        existing_specialty_ykihos = set(
            MedicalFacilitySpecialty.objects.values_list("mapping_id", flat=True).distinct()
        )
    matches_for_specialty = {
        hpid: (ykiho, Decimal("1.000"), "cached_mapping")
        for hpid, ykiho in mapping_pairs.items()
        if options.force or ykiho not in existing_specialty_ykihos
    }

    specialty_limit = _hira_specialty_max_calls(options)
    specialty_rows, specialty_stats = _specialty_rows_for_matches(
        matches_for_specialty,
        options,
        specialty_limit=specialty_limit,
    )
    fetched_facility_ids = specialty_stats.pop("fetched_facility_ids")
    fetched_ykihos = {
        matches_for_specialty[hpid][0]
        for hpid in fetched_facility_ids
        if hpid in matches_for_specialty
    }

    specialty_completed = (
        len(matches_for_specialty) == len(fetched_facility_ids)
        and not specialty_stats["failed"]
        and not specialty_stats["rate_limited"]
    )

    if not options.dry_run and fetched_ykihos:
        with transaction.atomic():
            MedicalFacilitySpecialty.objects.filter(mapping_id__in=fetched_ykihos).delete()
            MedicalFacilitySpecialty.objects.bulk_create(specialty_rows, batch_size=2000, ignore_conflicts=True)

    return {
        "status": "success" if options.dry_run or specialty_completed else "partial",
        "completed": bool(options.dry_run or specialty_completed),
        "dry_run": options.dry_run,
        "specialty": {
            **specialty_stats,
            "existing_hira_count": len(existing_specialty_ykihos) if not options.dry_run else None,
            "pending_hira_count": len(matches_for_specialty),
            "fetched_hira_count": len(fetched_ykihos),
            "max_calls": specialty_limit,
            "rows": len(specialty_rows),
            "sample": [
                {"hira_ykiho": row.mapping_id, "specialty_name": row.specialty_name, "specialist_count": row.specialist_count}
                for row in specialty_rows[:20]
            ],
        },
    }



def _contains_unsuccessful_result(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("error"):
            return True
        if value.get("completed") is False:
            return True
        if value.get("status") in {"rate_limited", "partial", "failed", "error"}:
            return True
        return any(_contains_unsuccessful_result(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_unsuccessful_result(item) for item in value)
    return False


def update_medical(options: MedicalUpdateOptions) -> dict[str, Any]:
    if options.limit is not None and not options.dry_run:
        raise RuntimeError("medical updater does not support --limit with --write because emergency/holiday tables are full-replacement datasets")
    facilities = _update_facilities(options)
    emergency = _update_emergency(options)
    holiday = _update_holiday(options)
    hira_mapping = _update_hira_mapping(options)
    hira_specialties = _update_hira_specialties(options)
    result = {
        "dry_run": options.dry_run,
        "facilities": facilities,
        "emergency": emergency,
        "holiday": holiday,
        "hira_mapping": hira_mapping,
        "hira_specialties": hira_specialties,
    }
    if _contains_unsuccessful_result(result):
        result["status"] = "partial"
        result["completed"] = False
    else:
        result["status"] = "success"
        result["completed"] = True
    return result


def update(options: MedicalUpdateOptions) -> dict[str, Any]:
    result: dict[str, Any] = {"dataset": "medical", "dry_run": options.dry_run, "medical": None}
    try:
        result["medical"] = update_medical(options)
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        if not options.dry_run:
            record_dataset_result("medical", result)
        raise
    if not options.dry_run:
        record_dataset_result("medical", result)
    return result
