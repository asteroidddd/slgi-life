from __future__ import annotations

from typing import Any

from django.db.models import Count
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.caches.region_stats.models import RegionAmenityCategoryCache
from apps.public_data.regions.models import Adong, Ldong
from apps.public_data.rent_deal.models import RentConversionRate
from apps.service.recommend.cache import load_rent_metrics
from apps.service.recommend.models import AdongUnivTime, LdongUnivTime


FACILITY_KEYS = {
    "convenience",
    "daiso",
    "laundry",
    "park",
    "gym",
    "pharmacy",
    "hospital",
    "library",
    "study_cafe",
}
DEFAULT_LIMIT = 5
MAX_LIMIT = 10
FALLBACK_MONTHLY_RATE = 0.005


@method_decorator(csrf_exempt, name="dispatch")
class RecommendationRegionsView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        conditions, error = _parse_conditions(request.data or {})
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        conversion = _latest_conversion_rate()
        monthly_rate = conversion["monthly_rate"]
        as_of_date = timezone.localdate()

        adong_items = _recommend_for_level(
            region_level="adong",
            conditions=conditions,
            monthly_rate=monthly_rate,
            conversion_period=conversion["period"],
            as_of_date=as_of_date,
        )
        ldong_items = _recommend_for_level(
            region_level="ldong",
            conditions=conditions,
            monthly_rate=monthly_rate,
            conversion_period=conversion["period"],
            as_of_date=as_of_date,
        )

        return Response(
            {
                "adongs": adong_items,
                "ldongs": ldong_items,
                "total": len(adong_items) + len(ldong_items),
                "basis": {
                    "conversion_rate_period": conversion["period"],
                    "conversion_monthly_rate": monthly_rate,
                    "facility_match": "all_selected",
                    "limit": conditions["limit"],
                },
            },
            status=status.HTTP_200_OK,
        )


def _parse_conditions(data: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    facilities = data.get("facilities") or []
    if not isinstance(facilities, list):
        return {}, "facilities must be a list."
    normalized_facilities = [str(item).strip() for item in facilities if str(item).strip()]
    invalid = sorted(set(normalized_facilities) - FACILITY_KEYS)
    if invalid:
        return {}, f"Unsupported facilities: {', '.join(invalid)}"

    priority = data.get("priority")
    if priority not in {"budget", "transport"}:
        priority = "budget"

    limit = _number(data.get("limit"), DEFAULT_LIMIT)
    limit = max(1, min(MAX_LIMIT, int(limit or DEFAULT_LIMIT)))

    return {
        "deposit": max(0.0, _number(data.get("deposit"), 0.0)),
        "monthly_rent": max(0.0, _number(data.get("monthlyRent"), 0.0)),
        "area_m2": _area_value(data.get("areaM2")),
        "facilities": normalized_facilities,
        "university_id": str(data.get("universityId") or "").strip(),
        "max_commute_minutes": max(0.0, _number(data.get("maxCommuteMinutes"), 0.0)),
        "priority": priority,
        "limit": limit,
    }, None


def _number(value: Any, default: float) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _area_value(value: Any) -> float | None:
    if value is None or value == "":
        return None
    area = _number(value, 0.0)
    return area if area > 0 else None


def _latest_conversion_rate() -> dict[str, Any]:
    row = RentConversionRate.objects.order_by("-period_ym").first()
    if not row:
        return {"period": None, "monthly_rate": FALLBACK_MONTHLY_RATE}
    return {"period": row.period_ym, "monthly_rate": row.monthly_rate}


def _recommend_for_level(
    *,
    region_level: str,
    conditions: dict[str, Any],
    monthly_rate: float,
    conversion_period: str | None,
    as_of_date,
) -> list[dict[str, Any]]:
    rent_metrics = _rent_metrics(region_level, monthly_rate, conversion_period, as_of_date)
    budget_codes = _budget_matching_codes(rent_metrics, conditions, monthly_rate)
    facility_codes = _facility_matching_codes(region_level, conditions["facilities"])
    travel_times = _travel_times(region_level, conditions["university_id"])

    codes = set(budget_codes)
    if facility_codes is not None:
        codes &= facility_codes
    if conditions["university_id"]:
        max_minutes = conditions["max_commute_minutes"]
        codes &= {code for code, minutes in travel_times.items() if max_minutes <= 0 or minutes <= max_minutes}

    items = _region_payloads(region_level, codes, rent_metrics, travel_times, conditions)
    items.sort(key=lambda item: _sort_key(item, conditions))
    limited = items[: conditions["limit"]]
    for index, item in enumerate(limited, start=1):
        item["rank"] = index
    return limited


def _rent_metrics(
    region_level: str,
    monthly_rate: float,
    conversion_period: str | None,
    as_of_date,
) -> dict[str, dict[str, float | None]]:
    return load_rent_metrics(
        region_level=region_level,
        monthly_rate=monthly_rate,
        conversion_rate_period=conversion_period,
        as_of_date=as_of_date,
    )

def _budget_matching_codes(
    rent_metrics: dict[str, dict[str, float | None]],
    conditions: dict[str, Any],
    monthly_rate: float,
) -> set[str]:
    user_converted = conditions["monthly_rent"] + conditions["deposit"] * monthly_rate
    area_m2 = conditions["area_m2"]
    result: set[str] = set()
    for code, metric in rent_metrics.items():
        if area_m2:
            region_value = metric["avg_per_m2"]
            user_value = user_converted / area_m2
        else:
            region_value = metric["median_converted"]
            user_value = user_converted
        if region_value is None:
            continue
        if region_value * 1.1 <= user_value:
            result.add(code)
    return result


def _facility_matching_codes(region_level: str, facilities: list[str]) -> set[str] | None:
    unique_facilities = sorted(set(facilities))
    if not unique_facilities:
        return None
    rows = (
        RegionAmenityCategoryCache.objects
        .filter(region_type=region_level, category__in=unique_facilities, amenity_count__gt=0)
        .values("region_code")
        .annotate(matched_categories=Count("category", distinct=True))
        .filter(matched_categories=len(unique_facilities))
        .values_list("region_code", flat=True)
    )
    return {str(code) for code in rows}

def _travel_times(region_level: str, university_id: str) -> dict[str, int]:
    if not university_id:
        return {}
    model = AdongUnivTime if region_level == "adong" else LdongUnivTime
    region_field = "adong_id" if region_level == "adong" else "ldong_id"
    return {
        str(code): int(minutes)
        for code, minutes in model.objects.filter(univ_id=university_id).values_list(region_field, "time")
    }


def _region_payloads(
    region_level: str,
    codes: set[str],
    rent_metrics: dict[str, dict[str, float | None]],
    travel_times: dict[str, int],
    conditions: dict[str, Any],
) -> list[dict[str, Any]]:
    if not codes:
        return []
    model = Adong if region_level == "adong" else Ldong
    code_field = "adong_code" if region_level == "adong" else "ldong_code"
    rows = model.objects.select_related("gu", "current_score").filter(**{f"{code_field}__in": codes})

    area_m2 = conditions["area_m2"]
    metric_key = "avg_per_m2" if area_m2 else "median_converted"
    metric_label = "m²당 환산월세" if area_m2 else "중위 환산월세"
    items: list[dict[str, Any]] = []
    for region in rows:
        code = str(getattr(region, code_field))
        current = getattr(region, "current_score", None)
        metric_value = rent_metrics.get(code, {}).get(metric_key)
        items.append(
            {
                "rank": 0,
                "region_level": region_level,
                "code": code,
                "slug": getattr(region, "slug", ""),
                "name": region.name,
                "gu": region.gu.name if getattr(region, "gu", None) else "",
                "score_rent": _optional_float(getattr(current, "score_rent", None)),
                "score_amenity": _score_value(getattr(current, "score_amenity", None)),
                "score_transit": _score_value(getattr(current, "score_transit", None)),
                "score_safety": _score_value(getattr(current, "score_safety", None)),
                "score_total": _score_value(getattr(current, "score_total", None)),
                "score": _score_value(getattr(current, "score_total", None)),
                "lat": region.location.y if getattr(region, "location", None) else 0,
                "lng": region.location.x if getattr(region, "location", None) else 0,
                "rent_metric": round(metric_value, 4) if isinstance(metric_value, float) else None,
                "rent_metric_label": metric_label,
                "travel_minutes": travel_times.get(code),
            }
        )
    return items


def _sort_key(item: dict[str, Any], conditions: dict[str, Any]) -> tuple[Any, ...]:
    if conditions["priority"] == "transport":
        if conditions["university_id"]:
            travel = item.get("travel_minutes")
            return (travel is None, travel if travel is not None else 10**9, item["rent_metric"] is None, item["rent_metric"] or 10**9)
        return (-float(item.get("score_transit") or 0), item["rent_metric"] is None, item["rent_metric"] or 10**9)
    return (item["rent_metric"] is None, item["rent_metric"] if item["rent_metric"] is not None else 10**9)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _score_value(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)
