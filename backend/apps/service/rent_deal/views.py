from __future__ import annotations

import hashlib
import json
import math
import zlib
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.db import connection
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public_data.rent_deal.models import DEAL_TYPE_TO_HOUSING_TYPE, RentDeal
from apps.public_data.rent_deal.serializers import RentDealPinSerializer
from apps.public_data.rent_deal.utils import get_conversion_rate_payload, get_monthly_conversion_rate
from apps.public_data.regions.models import Adong, Ldong, LdongAdjacency
from apps.service.map.views import _search_vworld


ALL_DEAL_TYPES: tuple[str, ...] = (
    "apt",
    "officetel",
    "yeonlip",
    "dasedae",
    "yeonlip_dasedae",
    "dagagu",
    "danok",
    "danok_dagagu",
    "villa",
)
DEFAULT_DEAL_TYPES: tuple[str, ...] = (
    "yeonlip",
    "dasedae",
    "yeonlip_dasedae",
    "dagagu",
    "danok",
    "officetel",
)
PERIOD_TO_DAYS: dict[str, int | None] = {
    "3m": 90,
    "6m": 180,
    "12m": 365,
    "24m": 730,
    "all": None,
}
MIN_SAMPLE = 10
CACHE_TTL = 300
FRONTEND_CACHE_TTL = 24 * 60 * 60
FILTER_MODES = ("converted", "raw")
TYPE_CODE_TO_DEAL_TYPE = {
    "A": "apt",
    "O": "officetel",
    "Y": "yeonlip",
    "D": "dasedae",
    "V": "yeonlip_dasedae",
    "M": "dagagu",
    "H": "danok",
    "S": "danok_dagagu",
}
CACHE_COLUMNS = ("id", "t", "d", "m", "c", "a", "lng", "lat", "dt")
SUMMARY_CACHE_VERSION = 1
LDONG_SUMMARY_COLUMNS = ("ldong_code", "gu_name", "ldong_name", "avg", "count", "lng", "lat")
GRID_SUMMARY_COLUMNS = ("grid_id", "gu_code", "gu_name", "avg", "count", "lng", "lat")
GU_CACHE_COLUMNS = CACHE_COLUMNS
DEAL_TYPE_TO_TYPE_CODE = {deal_type: code for code, deal_type in TYPE_CODE_TO_DEAL_TYPE.items()}
LISTING_LOOKBACK_DAYS = 730
LISTING_DECAY_DAYS = 180.0
LISTING_TYPE_GROUPS: dict[str, tuple[str, tuple[str, ...]]] = {
    "apartment": ("아파트", ("아파트",)),
    "apt": ("아파트", ("아파트",)),
    "아파트": ("아파트", ("아파트",)),
    "officetel": ("오피스텔", ("오피스텔",)),
    "오피스텔": ("오피스텔", ("오피스텔",)),
    "villa_house": ("빌라·주택", ("연립다세대", "다가구", "단독", "단독다가구")),
    "villa": ("빌라·주택", ("연립다세대", "다가구", "단독", "단독다가구")),
    "빌라": ("빌라·주택", ("연립다세대", "다가구", "단독", "단독다가구")),
    "빌라·주택": ("빌라·주택", ("연립다세대", "다가구", "단독", "단독다가구")),
    "빌라/주택": ("빌라·주택", ("연립다세대", "다가구", "단독", "단독다가구")),
}


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _iter_rent_deal_cache_payload() -> Any:
    header = {
        "version": 1,
        "ttl_seconds": FRONTEND_CACHE_TTL,
        "columns": CACHE_COLUMNS,
        "type_map": TYPE_CODE_TO_DEAL_TYPE,
        "rows": None,
    }
    prefix = _compact_json({k: v for k, v in header.items() if k != "rows"})
    yield prefix[:-1] + ',"rows":['

    first = True
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                '[' ||
                to_json(id)::text || ',' ||
                to_json(type_code)::text || ',' ||
                deposit::text || ',' ||
                monthly_rent::text || ',' ||
                converted_rent::text || ',' ||
                COALESCE(to_json(area_m2)::text, 'null') || ',' ||
                COALESCE(to_json(lng)::text, 'null') || ',' ||
                COALESCE(to_json(lat)::text, 'null') || ',' ||
                contract_ymd::text ||
                ']' AS row_json
            FROM rent_deal_cache
            """
        )
        while True:
            rows = cursor.fetchmany(10_000)
            if not rows:
                break
            for row in rows:
                if first:
                    first = False
                else:
                    yield ","
                yield row[0]
    yield "]}"




def _period_to_min_year_month(period: str, today: date) -> int | None:
    days = PERIOD_TO_DAYS[period]
    if days is None:
        return None
    start = today - timedelta(days=days)
    return start.year * 100 + start.month


def _type_codes_for_filters(filters: dict[str, Any]) -> tuple[str, ...]:
    codes: list[str] = []
    for deal_type in filters["deal_types"]:
        code = DEAL_TYPE_TO_TYPE_CODE.get(deal_type)
        if code and code not in codes:
            codes.append(code)
    return tuple(codes)


def _parse_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    try:
        lng1, lat1, lng2, lat2 = [float(item) for item in raw.split(",")]
    except (TypeError, ValueError) as exc:
        raise ValidationError({"bbox": "bbox must be lng1,lat1,lng2,lat2."}) from exc
    if lng1 > lng2 or lat1 > lat2:
        raise ValidationError({"bbox": "bbox min values must be <= max values."})
    return lng1, lat1, lng2, lat2


def _summary_params(request: Request) -> tuple[dict[str, Any], tuple[str, ...], int | None]:
    filters = parse_match_filters(request)
    type_codes = _type_codes_for_filters(filters)
    min_year_month = _period_to_min_year_month(filters["period"], today=date.today())
    return filters, type_codes, min_year_month


def _gzip_stream(chunks: Iterable[str]) -> Iterable[bytes]:
    compressor = zlib.compressobj(wbits=31)
    for chunk in chunks:
        if not chunk:
            continue
        data = compressor.compress(chunk.encode("utf-8"))
        if data:
            yield data
    tail = compressor.flush()
    if tail:
        yield tail


def _parse_csv_set(raw: str | None, allowed: tuple[str, ...]) -> tuple[str, ...]:
    if not raw:
        return ()
    items = [s.strip() for s in raw.split(",") if s.strip()]
    bad = [s for s in items if s not in allowed]
    if bad:
        raise ValidationError({"deal_types": f"unknown deal_types: {bad}"})
    seen = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return tuple(out)


def _parse_int(raw: str | None, key: str, default: int, lo: int, hi: int) -> int:
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValidationError({key: f"{key} must be an integer."}) from exc
    if value < lo or value > hi:
        raise ValidationError({key: f"{key} must be in {lo}..{hi}."})
    return value


def _expand_deal_types(deal_types: tuple[str, ...]) -> tuple[str, ...]:
    expanded: list[str] = []
    for key in deal_types:
        if key == "villa":
            expanded.extend(["yeonlip", "dasedae", "yeonlip_dasedae"])
        else:
            expanded.append(key)
    seen = set()
    out: list[str] = []
    for key in expanded:
        if key not in seen:
            out.append(key)
            seen.add(key)
    if "yeonlip" in seen and "dasedae" in seen and "yeonlip_dasedae" not in seen:
        out.append("yeonlip_dasedae")
    if "dagagu" in seen and "danok" in seen and "danok_dagagu" not in seen:
        out.append("danok_dagagu")
    return tuple(out)


def parse_match_filters(request: Request) -> dict[str, Any]:
    params = request.query_params
    deal_types = _parse_csv_set(params.get("deal_types"), ALL_DEAL_TYPES)
    if not deal_types:
        deal_types = DEFAULT_DEAL_TYPES
    deal_types = _expand_deal_types(deal_types)

    period = params.get("period", "6m")
    if period not in PERIOD_TO_DAYS:
        raise ValidationError({"period": f"period must be one of {list(PERIOD_TO_DAYS)}."})

    filter_mode = params.get("filter_mode", "converted")
    if filter_mode not in FILTER_MODES:
        raise ValidationError({"filter_mode": f"filter_mode must be one of {list(FILTER_MODES)}."})

    deposit_min = _parse_int(params.get("deposit_min"), "deposit_min", 0, 0, 10_000_000)
    deposit_max = _parse_int(params.get("deposit_max"), "deposit_max", 50_000, 0, 10_000_000)
    if deposit_min > deposit_max:
        raise ValidationError({"deposit_min": "deposit_min must be <= deposit_max."})

    monthly_min = _parse_int(params.get("monthly_min"), "monthly_min", 0, 0, 1_000_000)
    monthly_max = _parse_int(params.get("monthly_max"), "monthly_max", 300, 0, 1_000_000)
    if monthly_min > monthly_max:
        raise ValidationError({"monthly_min": "monthly_min must be <= monthly_max."})

    converted_min = _parse_int(params.get("converted_min"), "converted_min", 0, 0, 1_000_000)
    converted_max = _parse_int(params.get("converted_max"), "converted_max", 300, 0, 1_000_000)
    if converted_min > converted_max:
        raise ValidationError({"converted_min": "converted_min must be <= converted_max."})

    area_min = _parse_int(params.get("area_min"), "area_min", 10, 0, 10_000)
    area_max = _parse_int(params.get("area_max"), "area_max", 100, 0, 10_000)
    if area_min > area_max:
        raise ValidationError({"area_min": "area_min must be <= area_max."})

    return {
        "deal_types": deal_types,
        "period": period,
        "filter_mode": filter_mode,
        "deposit_min": deposit_min,
        "deposit_max": deposit_max,
        "monthly_min": monthly_min,
        "monthly_max": monthly_max,
        "converted_min": converted_min,
        "converted_max": converted_max,
        "area_min": area_min,
        "area_max": area_max,
    }


def _date_to_ymd(value: date) -> int:
    return value.year * 10000 + value.month * 100 + value.day


def _match_count_rows(filters: dict[str, Any], today: date) -> list[tuple[str, int]]:
    type_codes = _type_codes_for_filters(filters)
    if not type_codes:
        return []

    clauses = [
        "adong_code IS NOT NULL",
        "type_code = ANY(%s)",
        "area_m2 BETWEEN %s AND %s",
    ]
    params: list[Any] = [list(type_codes), filters["area_min"], filters["area_max"]]

    if filters["filter_mode"] == "raw":
        clauses.extend(
            [
                "deposit BETWEEN %s AND %s",
                "monthly_rent BETWEEN %s AND %s",
            ]
        )
        params.extend(
            [
                filters["deposit_min"],
                filters["deposit_max"],
                filters["monthly_min"],
                filters["monthly_max"],
            ]
        )
    else:
        clauses.append("converted_rent BETWEEN %s AND %s")
        params.extend([filters["converted_min"], filters["converted_max"]])

    days = PERIOD_TO_DAYS[filters["period"]]
    if days is not None:
        clauses.append("contract_ymd >= %s")
        params.append(_date_to_ymd(today - timedelta(days=days)))

    where_sql = " AND ".join(clauses)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT adong_code, COUNT(*)::int AS cnt
            FROM rent_deal_cache
            WHERE {where_sql}
            GROUP BY adong_code
            """,
            params,
        )
        return [(code, count) for code, count in cursor.fetchall()]


def _canonicalize_filters(filters: dict[str, Any]) -> str:
    canonical: dict[str, Any] = {}
    for key in sorted(filters):
        value = filters[key]
        if isinstance(value, (list, tuple)):
            value = ",".join(sorted(map(str, value)))
        canonical[key] = value
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _normalize_ratio(count: int, max_count: int) -> float:
    if count < MIN_SAMPLE or max_count <= 0:
        return 0.0
    return round(math.log1p(count) / math.log1p(max_count) * 100, 1)


def compute_match_counts(filters: dict[str, Any], today: date) -> dict[str, Any]:
    cache_key = f"rent-deal:match-counts:v2:{_canonicalize_filters(filters)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    counts_by_adong_code = {
        code: count
        for code, count in _match_count_rows(filters, today)
        if code is not None
    }

    adongs = list(Adong.objects.values("adong_code", "slug"))
    max_count = max(counts_by_adong_code.values()) if counts_by_adong_code else 0
    total_matched = sum(counts_by_adong_code.values())
    items = []
    for adong in adongs:
        count = counts_by_adong_code.get(adong["adong_code"], 0)
        items.append(
            {
                "code": adong["adong_code"],
                "slug": adong["slug"],
                "count": count,
                "ratio": _normalize_ratio(count, max_count),
                "has_data": True,
            }
        )

    response = {
        "filters_applied": filters,
        "total_matched": total_matched,
        "min_sample": MIN_SAMPLE,
        "adongs": items,
    }
    cache.set(cache_key, response, CACHE_TTL)
    return response


def _parse_listing_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _parse_listing_float(data: dict[str, Any], key: str, *, min_value: float, max_value: float) -> float:
    raw = data.get(key)
    if raw in (None, ""):
        raise ValidationError({key: f"{key} is required."})
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({key: f"{key} must be a number."}) from exc
    if value < min_value or value > max_value:
        raise ValidationError({key: f"{key} must be in {min_value}..{max_value}."})
    return value


def _parse_listing_payload(data: dict[str, Any]) -> dict[str, Any]:
    address = str(data.get("address") or "").strip()
    if len(address) < 2:
        raise ValidationError({"address": "address is required."})
    raw_type = str(data.get("housing_type") or data.get("listing_type") or "").strip()
    if raw_type not in LISTING_TYPE_GROUPS:
        raise ValidationError({"housing_type": "housing_type must be apartment, officetel, or villa_house."})
    type_label, housing_types = LISTING_TYPE_GROUPS[raw_type]
    area_m2 = _parse_listing_float(data, "area_m2", min_value=1.0, max_value=1000.0)
    deposit = _parse_listing_float(data, "deposit", min_value=0.0, max_value=10_000_000.0)
    monthly_rent = _parse_listing_float(data, "monthly_rent", min_value=0.0, max_value=1_000_000.0)
    return {
        "address": address,
        "area_m2": area_m2,
        "deposit": deposit,
        "monthly_rent": monthly_rent,
        "housing_type": raw_type,
        "housing_type_label": type_label,
        "housing_types": housing_types,
        "include_adjacent": _parse_listing_bool(data.get("include_adjacent")),
    }


def _ldong_for_point(lat: float, lng: float) -> Ldong | None:
    point = Point(lng, lat, srid=4326)
    return (
        Ldong.objects.select_related("gu")
        .filter(boundary__contains=point)
        .order_by("gu__name", "name")
        .first()
    )


def _ldong_from_address_text(address: str) -> Ldong | None:
    strict: list[Ldong] = []
    loose: list[Ldong] = []
    for ldong in Ldong.objects.select_related("gu").all():
        if ldong.name not in address:
            continue
        if ldong.gu.name in address:
            strict.append(ldong)
        else:
            loose.append(ldong)
    if strict:
        return sorted(strict, key=lambda row: len(row.name), reverse=True)[0]
    return loose[0] if len(loose) == 1 else None


def _resolve_listing_ldong(address: str) -> tuple[Ldong, dict[str, Any]]:
    cache_key = f"rent-listing:address:v1:{hashlib.sha1(address.encode('utf-8')).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        ldong = Ldong.objects.select_related("gu").filter(ldong_code=cached.get("ldong_code")).first()
        if ldong:
            return ldong, cached.get("source") or {"method": "cache"}

    for item in _search_vworld(address, limit=5):
        lat = item.get("lat")
        lng = item.get("lng")
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            continue
        ldong = _ldong_for_point(float(lat), float(lng))
        if ldong:
            source = {
                "method": "vworld",
                "lat": float(lat),
                "lng": float(lng),
                "matched_name": item.get("name") or "",
                "matched_address": item.get("address") or "",
            }
            cache.set(cache_key, {"ldong_code": ldong.ldong_code, "source": source}, timeout=60 * 60)
            return ldong, source

    ldong = _ldong_from_address_text(address)
    if ldong:
        source = {"method": "text", "matched_address": address}
        cache.set(cache_key, {"ldong_code": ldong.ldong_code, "source": source}, timeout=60 * 60)
        return ldong, source
    raise ValidationError({"address": "주소에서 법정동을 찾지 못했습니다. 서울 주소를 더 구체적으로 입력해 주세요."})


def _included_ldong_codes(ldong: Ldong, include_adjacent: bool) -> tuple[list[str], list[dict[str, str]]]:
    codes = {ldong.ldong_code}
    if include_adjacent:
        rows = LdongAdjacency.objects.select_related("ldong_a", "ldong_a__gu", "ldong_b", "ldong_b__gu").filter(
            Q(ldong_a_id=ldong.ldong_code) | Q(ldong_b_id=ldong.ldong_code)
        )
        for row in rows:
            codes.add(row.ldong_b_id if row.ldong_a_id == ldong.ldong_code else row.ldong_a_id)
    regions = [
        {"code": row.ldong_code, "gu_name": row.gu.name, "dong_name": row.name, "slug": row.slug or ""}
        for row in Ldong.objects.select_related("gu").filter(ldong_code__in=codes).order_by("gu__name", "name")
    ]
    return [row["code"] for row in regions], regions


def _max_contract_date() -> date:
    with connection.cursor() as cursor:
        cursor.execute("SELECT max(contract_date) FROM rent_deal")
        value = cursor.fetchone()[0]
    return value or date.today()


def _weighted_quantile(points: list[tuple[float, float]], quantile: float) -> float | None:
    if not points:
        return None
    ordered = sorted(points, key=lambda item: item[0])
    total_weight = sum(weight for _value, weight in ordered)
    if total_weight <= 0:
        return None
    cutoff = total_weight * quantile
    running = 0.0
    for value, weight in ordered:
        running += weight
        if running >= cutoff:
            return value
    return ordered[-1][0]


def _weighted_percentile_rank(points: list[tuple[float, float]], value: float) -> float | None:
    total_weight = sum(weight for _value, weight in points)
    if total_weight <= 0:
        return None
    below = sum(weight for sample, weight in points if sample < value)
    equal = sum(weight for sample, weight in points if sample == value)
    return round((below + equal * 0.5) / total_weight * 100.0, 1)


def _verdict_from_percentile(percentile: float | None) -> dict[str, str]:
    if percentile is None:
        return {"label": "판단 어려움", "tone": "info", "description": "비교 가능한 실거래 표본이 부족합니다."}
    if percentile < 20:
        return {"label": "저렴한 편", "tone": "good", "description": "시간 감쇠를 적용한 실거래 분포의 하위 20% 구간입니다."}
    if percentile < 40:
        return {"label": "낮은 편", "tone": "good", "description": "시간 감쇠를 적용한 실거래 분포에서 중위값보다 낮은 구간입니다."}
    if percentile <= 60:
        return {"label": "비슷한 편", "tone": "info", "description": "시간 감쇠를 적용한 실거래 중간 구간입니다."}
    if percentile <= 80:
        return {"label": "비싼 편", "tone": "bad", "description": "시간 감쇠를 적용한 실거래 분포에서 중위값보다 높은 구간입니다."}
    return {"label": "매우 비싼 편", "tone": "bad", "description": "시간 감쇠를 적용한 실거래 분포의 상위 20% 구간입니다."}


def _confidence(effective_sample_count: float) -> tuple[str, str]:
    if effective_sample_count >= 30:
        return "high", "높음"
    if effective_sample_count >= 10:
        return "medium", "보통"
    return "low", "낮음"


def _listing_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    ldong, address_source = _resolve_listing_ldong(payload["address"])
    max_date = _max_contract_date()
    start_date = max_date - timedelta(days=LISTING_LOOKBACK_DAYS)
    monthly_rate = get_monthly_conversion_rate()
    conversion_payload = get_conversion_rate_payload()
    converted_rent = payload["monthly_rent"] + payload["deposit"] * monthly_rate
    rent_per_area = converted_rent / payload["area_m2"]
    ldong_codes, included_regions = _included_ldong_codes(ldong, payload["include_adjacent"])

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ((monthly_rent + deposit * %s) / NULLIF(area_m2, 0))::float AS rent_per_area,
                contract_date,
                housing_type
            FROM rent_deal
            WHERE ldong_code = ANY(%s)
              AND housing_type = ANY(%s)
              AND contract_date >= %s
              AND area_m2 IS NOT NULL
              AND area_m2 > 0
            """,
            [monthly_rate, ldong_codes, list(payload["housing_types"]), start_date],
        )
        rows = cursor.fetchall()

    points: list[tuple[float, float]] = []
    type_counts: dict[str, int] = {}
    min_date: date | None = None
    max_sample_date: date | None = None
    for value, contract_date, housing_type in rows:
        if value is None or contract_date is None:
            continue
        days_ago = max(0, (max_date - contract_date).days)
        weight = math.exp(-days_ago / LISTING_DECAY_DAYS)
        points.append((float(value), weight))
        type_counts[housing_type] = type_counts.get(housing_type, 0) + 1
        min_date = contract_date if min_date is None or contract_date < min_date else min_date
        max_sample_date = contract_date if max_sample_date is None or contract_date > max_sample_date else max_sample_date

    sample_count = len(points)
    total_weight = sum(weight for _value, weight in points)
    weight_square_sum = sum(weight * weight for _value, weight in points)
    effective_sample_count = (total_weight * total_weight / weight_square_sum) if weight_square_sum else 0.0
    confidence, confidence_label = _confidence(effective_sample_count)

    q20 = _weighted_quantile(points, 0.2)
    q40 = _weighted_quantile(points, 0.4)
    median = _weighted_quantile(points, 0.5)
    q60 = _weighted_quantile(points, 0.6)
    q80 = _weighted_quantile(points, 0.8)
    percentile = _weighted_percentile_rank(points, rent_per_area)
    verdict = _verdict_from_percentile(percentile)
    delta_to_median_pct = ((rent_per_area - median) / median * 100.0) if median else None
    status_value = "ok" if sample_count else "no_data"

    region_name = f"{ldong.gu.name} {ldong.name}"
    if sample_count:
        verdict["summary"] = (
            f"{region_name} {payload['housing_type_label']} 최근 24개월 실거래 {sample_count}건에 "
            f"시간 감쇠를 적용한 결과, 입력 매물은 {verdict['label']}입니다."
        )
    else:
        verdict["summary"] = f"{region_name} {payload['housing_type_label']} 비교 표본이 없습니다."

    return {
        "status": status_value,
        "input": {
            "address": payload["address"],
            "area_m2": round(payload["area_m2"], 2),
            "deposit": round(payload["deposit"], 1),
            "monthly_rent": round(payload["monthly_rent"], 1),
            "converted_monthly_rent": round(converted_rent, 1),
            "rent_per_area": round(rent_per_area, 3),
            "housing_type": payload["housing_type"],
            "housing_type_label": payload["housing_type_label"],
            "include_adjacent": payload["include_adjacent"],
        },
        "region": {
            "code": ldong.ldong_code,
            "slug": ldong.slug or "",
            "gu_name": ldong.gu.name,
            "dong_name": ldong.name,
            "name": region_name,
            "address_source": address_source,
            "included_regions": included_regions,
        },
        "comparison": {
            "scope": "인근 법정동 포함" if payload["include_adjacent"] else "같은 법정동",
            "lookback_days": LISTING_LOOKBACK_DAYS,
            "decay_days": LISTING_DECAY_DAYS,
            "housing_type_label": payload["housing_type_label"],
            "housing_types": list(payload["housing_types"]),
            "sample_count": sample_count,
            "effective_sample_count": round(effective_sample_count, 1),
            "confidence": confidence,
            "confidence_label": confidence_label,
            "min_contract_date": min_date.isoformat() if min_date else None,
            "max_contract_date": max_sample_date.isoformat() if max_sample_date else None,
            "type_counts": type_counts,
        },
        "stats": {
            "q20": round(q20, 3) if q20 is not None else None,
            "q40": round(q40, 3) if q40 is not None else None,
            "median": round(median, 3) if median is not None else None,
            "q60": round(q60, 3) if q60 is not None else None,
            "q80": round(q80, 3) if q80 is not None else None,
            "weighted_percentile": percentile,
            "delta_to_median_pct": round(delta_to_median_pct, 1) if delta_to_median_pct is not None else None,
        },
        "verdict": verdict,
        "basis": {
            **conversion_payload,
            "period": "최근 24개월",
            "weight_formula": "exp(-days_ago / 180)",
            "unit": "만원/㎡",
        },
        "disclaimer": "실거래 기반 참고용입니다. 관리비, 옵션, 층, 건축연도, 채광, 수리 상태, 보증보험 가능 여부는 반영하지 않습니다.",
    }




def _ldong_summary_payload(request: Request) -> dict[str, Any]:
    filters, type_codes, min_year_month = _summary_params(request)
    params: list[Any] = [list(type_codes)]
    month_clause = ""
    if min_year_month is not None:
        month_clause = "AND year_month >= %s"
        params.append(min_year_month)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                ldong_code,
                gu_name,
                ldong_name,
                ROUND(SUM(avg_converted_rent::bigint * deal_count)::double precision / NULLIF(SUM(deal_count), 0))::integer AS avg_converted_rent,
                SUM(deal_count)::integer AS deal_count,
                AVG(center_lng) AS center_lng,
                AVG(center_lat) AS center_lat
            FROM rent_deal_ldong_monthly_cache
            WHERE type_code = ANY(%s)
              {month_clause}
            GROUP BY ldong_code, gu_name, ldong_name
            HAVING SUM(deal_count) > 0
            ORDER BY gu_name, ldong_name
            """,
            params,
        )
        rows = cursor.fetchall()
    return {
        "version": SUMMARY_CACHE_VERSION,
        "ttl_seconds": FRONTEND_CACHE_TTL,
        "columns": LDONG_SUMMARY_COLUMNS,
        "filters_applied": filters,
        "rows": [
            [code, gu, name, avg, count, lng, lat]
            for code, gu, name, avg, count, lng, lat in rows
        ],
    }


def _grid_summary_payload(request: Request) -> dict[str, Any]:
    filters, type_codes, min_year_month = _summary_params(request)
    bbox = _parse_bbox(request.query_params.get("bbox"))
    params: list[Any] = [list(type_codes)]
    clauses = ["type_code = ANY(%s)"]
    if min_year_month is not None:
        clauses.append("year_month >= %s")
        params.append(min_year_month)
    if bbox is not None:
        lng1, lat1, lng2, lat2 = bbox
        clauses.append("center_lng BETWEEN %s AND %s AND center_lat BETWEEN %s AND %s")
        params.extend([lng1, lng2, lat1, lat2])
    where_sql = " AND ".join(clauses)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                grid_id,
                gu_code,
                gu_name,
                ROUND(SUM(avg_converted_rent::bigint * deal_count)::double precision / NULLIF(SUM(deal_count), 0))::integer AS avg_converted_rent,
                SUM(deal_count)::integer AS deal_count,
                AVG(center_lng) AS center_lng,
                AVG(center_lat) AS center_lat
            FROM rent_deal_grid_monthly_cache
            WHERE {where_sql}
            GROUP BY grid_id, gu_code, gu_name
            HAVING SUM(deal_count) > 0
            ORDER BY deal_count DESC
            LIMIT 5000
            """,
            params,
        )
        rows = cursor.fetchall()
    return {
        "version": SUMMARY_CACHE_VERSION,
        "ttl_seconds": FRONTEND_CACHE_TTL,
        "grid_size_m": 300,
        "columns": GRID_SUMMARY_COLUMNS,
        "filters_applied": filters,
        "rows": [
            [grid_id, gu_code, gu_name, avg, count, lng, lat]
            for grid_id, gu_code, gu_name, avg, count, lng, lat in rows
        ],
    }


def _gu_codes_payload(request: Request) -> dict[str, Any]:
    bbox = _parse_bbox(request.query_params.get("bbox"))
    params: list[Any] = []
    where_sql = ""
    if bbox is not None:
        lng1, lat1, lng2, lat2 = bbox
        where_sql = """
        WHERE boundary && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
          AND ST_Intersects(boundary, ST_MakeEnvelope(%s, %s, %s, %s, 4326))
        """
        params.extend([lng1, lat1, lng2, lat2, lng1, lat1, lng2, lat2])
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT gu_code, name
            FROM gu
            {where_sql}
            ORDER BY gu_code
            """,
            params,
        )
        rows = cursor.fetchall()
    return {
        "version": SUMMARY_CACHE_VERSION,
        "ttl_seconds": FRONTEND_CACHE_TTL,
        "items": [{"gu_code": code, "gu_name": name} for code, name in rows],
    }


def _iter_gu_tsv(gu_code: str) -> Iterable[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                c.id,
                c.type_code,
                c.deposit,
                c.monthly_rent,
                c.converted_rent,
                c.area_m2,
                c.lng,
                c.lat,
                c.contract_ymd
            FROM rent_deal_cache c
            WHERE c.gu_code = %s
              AND c.lng IS NOT NULL
              AND c.lat IS NOT NULL
            """,
            [gu_code],
        )
        while True:
            rows = cursor.fetchmany(20_000)
            if not rows:
                break
            for row in rows:
                yield "\t".join("" if value is None else str(value) for value in row) + "\n"


class RentDealLdongSummaryView(APIView):
    def get(self, request: Request) -> Response:
        return Response(_ldong_summary_payload(request), status=status.HTTP_200_OK)


class RentDealGridSummaryView(APIView):
    def get(self, request: Request) -> Response:
        return Response(_grid_summary_payload(request), status=status.HTTP_200_OK)


class RentDealGuCodesView(APIView):
    def get(self, request: Request) -> Response:
        return Response(_gu_codes_payload(request), status=status.HTTP_200_OK)


class RentDealGuCacheView(APIView):
    def get(self, request: Request, gu_code: str) -> StreamingHttpResponse:
        response = StreamingHttpResponse(
            _gzip_stream(_iter_gu_tsv(gu_code)),
            content_type="text/tab-separated-values; charset=utf-8",
        )
        response["Content-Encoding"] = "gzip"
        response["Cache-Control"] = f"public, max-age={FRONTEND_CACHE_TTL}"
        response["Content-Disposition"] = f'inline; filename="rent-deals-{gu_code}.tsv.gz"'
        response["X-Accel-Buffering"] = "no"
        return response

class RentDealMatchCountsView(APIView):
    def get(self, request: Request) -> Response:
        filters = parse_match_filters(request)
        return Response(compute_match_counts(filters, today=date.today()), status=status.HTTP_200_OK)


class RentDealListingAnalysisView(APIView):
    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def post(self, request: Request) -> Response:
        payload = _parse_listing_payload(request.data)
        return Response(_listing_analysis(payload), status=status.HTTP_200_OK)


class RentDealCacheView(APIView):
    def get(self, request: Request) -> StreamingHttpResponse:
        response = StreamingHttpResponse(
            _iter_rent_deal_cache_payload(),
            content_type="application/json",
        )
        response["Cache-Control"] = f"public, max-age={FRONTEND_CACHE_TTL}"
        response["X-Accel-Buffering"] = "no"
        return response


class RentDealDetailView(APIView):
    def get(self, request: Request, deal_id: str) -> Response:
        deal = get_object_or_404(
            RentDeal.objects.select_related("ldong", "ldong__gu").filter(location__isnull=False),
            pk=deal_id,
        )
        return Response(RentDealPinSerializer(deal).data, status=status.HTTP_200_OK)


class RentDealConversionRateView(APIView):
    def get(self, request: Request) -> Response:
        return Response(get_conversion_rate_payload(), status=status.HTTP_200_OK)
