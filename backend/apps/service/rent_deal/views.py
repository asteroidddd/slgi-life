from __future__ import annotations

import hashlib
import json
import math
from datetime import date, timedelta
from typing import Any

from django.core.cache import cache
from django.db import connection
from django.db.models import Count, ExpressionWrapper, F, FloatField
from django.db.models.query import QuerySet
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public_data.rent_deal.models import DEAL_TYPE_TO_HOUSING_TYPE, RentDeal
from apps.public_data.rent_deal.serializers import RentDealPinSerializer
from apps.public_data.rent_deal.utils import get_annual_conversion_rate, get_monthly_conversion_rate
from apps.public_data.regions.models import Adong


ALL_DEAL_TYPES: tuple[str, ...] = (
    "apt",
    "officetel",
    "yeonlip",
    "dasedae",
    "yeonlip_dasedae",
    "dagagu",
    "danok",
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
}
CACHE_COLUMNS = ("id", "t", "d", "m", "c", "a", "lng", "lat", "dt")


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


def apply_match_filters(qs: QuerySet[RentDeal], filters: dict[str, Any], today: date) -> QuerySet[RentDeal]:
    housing_types = [
        DEAL_TYPE_TO_HOUSING_TYPE[key]
        for key in filters["deal_types"]
        if key in DEAL_TYPE_TO_HOUSING_TYPE
    ]
    base_filters = {
        "housing_type__in": housing_types,
        "area_m2__gte": filters["area_min"],
        "area_m2__lte": filters["area_max"],
    }
    if filters["filter_mode"] == "raw":
        base_filters.update(
            {
                "deposit__gte": filters["deposit_min"],
                "deposit__lte": filters["deposit_max"],
                "monthly_rent__gte": filters["monthly_min"],
                "monthly_rent__lte": filters["monthly_max"],
            }
        )
        qs = qs.filter(**base_filters)
    else:
        monthly_rate = get_monthly_conversion_rate()
        qs = (
            qs.filter(**base_filters)
            .annotate(
                converted_rent_calc=ExpressionWrapper(
                    F("monthly_rent") + F("deposit") * monthly_rate,
                    output_field=FloatField(),
                )
            )
            .filter(
                converted_rent_calc__gte=filters["converted_min"],
                converted_rent_calc__lte=filters["converted_max"],
            )
        )
    days = PERIOD_TO_DAYS[filters["period"]]
    if days is not None:
        qs = qs.filter(contract_date__gte=today - timedelta(days=days))
    return qs


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
    cache_key = f"rent-deal:match-counts:{_canonicalize_filters(filters)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = apply_match_filters(RentDeal.objects.filter(adong_id__isnull=False), filters, today)
    rows = qs.values("adong_id").annotate(cnt=Count("id"))
    counts_by_adong_code = {
        row["adong_id"]: row["cnt"]
        for row in rows
        if row["adong_id"] is not None
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


class RentDealMatchCountsView(APIView):
    def get(self, request: Request) -> Response:
        filters = parse_match_filters(request)
        return Response(compute_match_counts(filters, today=date.today()), status=status.HTTP_200_OK)


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
        annual_rate = get_annual_conversion_rate()
        return Response(
            {
                "annual_rate": annual_rate,
                "monthly_rate": annual_rate / 100.0 / 12.0,
                "source": "KOSIS 한국부동산원 전월세전환율",
                "unit": "percent_per_year",
            },
            status=status.HTTP_200_OK,
        )
