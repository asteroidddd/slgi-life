from __future__ import annotations

import hashlib
import math
from datetime import date, timedelta
from typing import Any

from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.db import connection
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public_data.rent_deal.utils import get_conversion_rate_payload, get_monthly_conversion_rate
from apps.public_data.regions.models import Ldong, LdongAdjacency
from apps.service.map.views import _search_vworld


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


class RentDealListingAnalysisView(APIView):
    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def post(self, request: Request) -> Response:
        payload = _parse_listing_payload(request.data)
        return Response(_listing_analysis(payload), status=status.HTTP_200_OK)


class RentDealConversionRateView(APIView):
    def get(self, request: Request) -> Response:
        return Response(get_conversion_rate_payload(), status=status.HTTP_200_OK)
