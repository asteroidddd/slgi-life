from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.cache.models import DashboardAdongCache, DashboardLdongCache
from apps.public_data.univ.models import Univ
from apps.service.recommend.models import AdongUnivTime, LdongUnivTime

MAX_COMPARE_ITEMS = 10
REGION_LEVELS = {"adong", "ldong"}


def _parse_region_keys(raw: str | None) -> list[tuple[str, str]]:
    if not raw:
        raise ValidationError({"regions": "regions is required."})

    items: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for token in raw.split(","):
        value = token.strip()
        if not value:
            continue
        region_level, separator, slug = value.partition(":")
        region_level = region_level.strip()
        slug = slug.strip()
        if not separator or region_level not in REGION_LEVELS or not slug:
            raise ValidationError({"regions": "Each item must be formatted as adong:slug or ldong:slug."})
        key = (region_level, slug)
        if key in seen:
            continue
        seen.add(key)
        items.append(key)
        if len(items) >= MAX_COMPARE_ITEMS:
            break

    if not items:
        raise ValidationError({"regions": "At least one region is required."})
    return items


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _score_payload(region: Any) -> dict[str, float | int | None]:
    current = getattr(region, "current_score", None)
    return {
        "total": _number(getattr(current, "score_total", None)),
        "rent": _number(getattr(current, "score_rent", None)),
        "transit": _number(getattr(current, "score_transit", None)),
        "amenity": _number(getattr(current, "score_amenity", None)),
        "safety": _number(getattr(current, "score_safety", None)),
        "rank_total": getattr(current, "rank_total", None) if current else None,
        "rank_rent": getattr(current, "rank_rent", None) if current else None,
        "rank_transit": getattr(current, "rank_transit", None) if current else None,
        "rank_amenity": getattr(current, "rank_amenity", None) if current else None,
        "rank_safety": getattr(current, "rank_safety", None) if current else None,
    }


def _metrics(items: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    result: list[dict[str, Any]] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "key": str(item.get("key") or item.get("label") or ""),
                "label": str(item.get("label") or item.get("key") or ""),
                "value": item.get("value"),
                "unit": item.get("unit") or "",
                "tone": item.get("tone") or "info",
                "badge": item.get("badge") or "",
                "description": item.get("description") or "",
            }
        )
    return result


def _quicktakes(items: Any, *, limit: int = 4) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []
    result: list[dict[str, str]] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        result.append({"label": label.strip(), "tone": str(item.get("tone") or "info")})
    return result


def _compact_items(items: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    result: list[dict[str, Any]] = []
    for item in items[:limit]:
        if isinstance(item, dict):
            result.append(item)
    return result


def _university(university_id: str | None) -> Univ | None:
    if not university_id:
        return None
    university = Univ.objects.filter(id=university_id).first()
    if university is None:
        raise ValidationError({"university_id": "Unknown university_id."})
    return university


def _university_payload(university: Univ | None) -> dict[str, str] | None:
    if university is None:
        return None
    return {"id": university.id, "name": university.name}


def _travel_times(region_level: str, codes: list[str], university: Univ | None) -> dict[str, int]:
    if university is None or not codes:
        return {}
    if region_level == "adong":
        return {
            str(code): int(minutes)
            for code, minutes in AdongUnivTime.objects
            .filter(univ=university, adong_id__in=codes)
            .values_list("adong_id", "time")
        }
    return {
        str(code): int(minutes)
        for code, minutes in LdongUnivTime.objects
        .filter(univ=university, ldong_id__in=codes)
        .values_list("ldong_id", "time")
    }


def _section(payload: dict[str, Any], section_key: str) -> dict[str, Any]:
    section = payload.get(section_key) or {}
    if not isinstance(section, dict):
        section = {}
    overview = section.get("overview") or {}
    if not isinstance(overview, dict):
        overview = {}

    data: dict[str, Any] = {
        "headline": overview.get("headline") or "",
        "summary": overview.get("summary") or "",
        "quicktakes": _quicktakes(overview.get("quicktakes")),
        "metrics": _metrics(overview.get("metrics")),
    }

    if section_key == "transit_summary":
        data["station_items"] = _compact_items(overview.get("station_items"), limit=4)
        data["station_names"] = overview.get("station_names") if isinstance(overview.get("station_names"), list) else []
    elif section_key == "infra_summary":
        category_mix = section.get("category_mix") or {}
        data["category_items"] = _compact_items(category_mix.get("items") if isinstance(category_mix, dict) else None)
    elif section_key == "safety_summary":
        grades = section.get("grades") or {}
        data["grade_items"] = _compact_items(grades.get("items") if isinstance(grades, dict) else None)

    return data


def _region_payload(
    cache: DashboardAdongCache | DashboardLdongCache,
    region_level: str,
    *,
    university: Univ | None = None,
    travel_minutes: int | None = None,
) -> dict[str, Any]:
    region = cache.adong if region_level == "adong" else cache.ldong
    code = getattr(region, "adong_code", None) or getattr(region, "ldong_code", "")
    payload = cache.dashboard_payload or {}
    region_payload = payload.get("region") or cache.region_payload or {}
    if not isinstance(region_payload, dict):
        region_payload = {}

    return {
        "key": f"{region_level}:{region.slug}",
        "regionLevel": region_level,
        "code": code,
        "slug": region.slug,
        "gu": region.gu.name if getattr(region, "gu", None) else region_payload.get("gu_name", ""),
        "name": region.name,
        "lat": region.location.y if getattr(region, "location", None) else None,
        "lng": region.location.x if getattr(region, "location", None) else None,
        "area_km2": region_payload.get("area_km2"),
        "intro": payload.get("intro") or cache.intro or "",
        "computed_at": payload.get("computed_at") or cache.computed_at.isoformat(),
        "commute": {
            "university": _university_payload(university),
            "travel_minutes": travel_minutes,
        },
        "scores": _score_payload(region),
        "sections": {
            "rent": _section(payload, "rent_summary"),
            "transit": _section(payload, "transit_summary"),
            "infra": _section(payload, "infra_summary"),
            "safety": _section(payload, "safety_summary"),
        },
    }


def _load_cache_map(region_level: str, slugs: list[str]) -> dict[str, DashboardAdongCache | DashboardLdongCache]:
    if region_level == "adong":
        rows = (
            DashboardAdongCache.objects
            .select_related("adong", "adong__gu", "adong__current_score")
            .filter(adong__slug__in=slugs)
        )
        return {row.adong.slug: row for row in rows}

    rows = (
        DashboardLdongCache.objects
        .select_related("ldong", "ldong__gu", "ldong__current_score")
        .filter(ldong__slug__in=slugs)
    )
    return {row.ldong.slug: row for row in rows}


class NeighborhoodCompareView(APIView):
    def get(self, request) -> Response:
        keys = _parse_region_keys(request.query_params.get("regions"))
        university = _university(request.query_params.get("university_id"))
        requested_by_level = {
            "adong": [slug for level, slug in keys if level == "adong"],
            "ldong": [slug for level, slug in keys if level == "ldong"],
        }
        caches = {
            "adong": _load_cache_map("adong", requested_by_level["adong"]),
            "ldong": _load_cache_map("ldong", requested_by_level["ldong"]),
        }
        travel_times = {
            "adong": _travel_times("adong", [cache.adong_id for cache in caches["adong"].values()], university),
            "ldong": _travel_times("ldong", [cache.ldong_id for cache in caches["ldong"].values()], university),
        }

        items: list[dict[str, Any]] = []
        missing: list[dict[str, str]] = []
        for region_level, slug in keys:
            cache = caches[region_level].get(slug)
            if cache is None:
                missing.append({"regionLevel": region_level, "slug": slug, "reason": "dashboard_cache_not_found"})
                continue
            code = cache.adong_id if region_level == "adong" else cache.ldong_id
            items.append(
                _region_payload(
                    cache,
                    region_level,
                    university=university,
                    travel_minutes=travel_times[region_level].get(str(code)),
                )
            )

        return Response(
            {
                "max_items": MAX_COMPARE_ITEMS,
                "items": items,
                "missing": missing,
            },
            status=status.HTTP_200_OK,
        )


class NeighborhoodCommuteTimeView(APIView):
    def get(self, request) -> Response:
        region_level = request.query_params.get("region_type") or request.query_params.get("regionLevel")
        slug = request.query_params.get("slug")
        university = _university(request.query_params.get("university_id"))
        if region_level not in REGION_LEVELS:
            raise ValidationError({"region_type": "region_type must be adong or ldong."})
        if not slug:
            raise ValidationError({"slug": "slug is required."})
        if university is None:
            raise ValidationError({"university_id": "university_id is required."})

        cache = _load_cache_map(region_level, [slug]).get(slug)
        if cache is None:
            return Response({"detail": "dashboard cache not found."}, status=status.HTTP_404_NOT_FOUND)

        code = cache.adong_id if region_level == "adong" else cache.ldong_id
        minutes = _travel_times(region_level, [str(code)], university).get(str(code))
        region = cache.adong if region_level == "adong" else cache.ldong
        return Response(
            {
                "regionLevel": region_level,
                "slug": slug,
                "code": code,
                "gu": region.gu.name if getattr(region, "gu", None) else "",
                "name": region.name,
                "university": _university_payload(university),
                "travel_minutes": minutes,
            },
            status=status.HTTP_200_OK,
        )
