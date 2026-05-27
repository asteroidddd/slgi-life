from __future__ import annotations

import json
import math
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.cache import cache


VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"
SEOUL_SEARCH_BBOX = "126.72,37.34,127.22,37.75"


def _make_item(raw: dict, search_type: str, query: str) -> dict | None:
    point = raw.get("point") or {}
    try:
        lng = float(point.get("x"))
        lat = float(point.get("y"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(lng) or not math.isfinite(lat):
        return None

    address_obj = raw.get("address") or {}
    road = str(address_obj.get("road") or "").strip()
    parcel = str(address_obj.get("parcel") or "").strip()
    district = str(raw.get("district") or "").strip()
    title = str(raw.get("title") or road or parcel or query).strip()
    label = {
        "place": str(raw.get("category") or "장소"),
        "address": "주소",
        "district": "행정구역",
        "road": "도로명",
    }.get(search_type, search_type)

    return {
        "id": f"vworld:{search_type}:{raw.get('id') or lng},{lat}",
        "source": "vworld",
        "type": search_type,
        "name": title,
        "label": label,
        "address": road or parcel or district,
        "lat": lat,
        "lng": lng,
    }


def _vworld_request(query: str, search_type: str, *, category: str | None = None, size: int = 5) -> list[dict]:
    key = os.environ.get("V_WORLD_API_KEY", "").strip()
    if not key:
        return []

    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "bbox": SEOUL_SEARCH_BBOX,
        "size": str(size),
        "page": "1",
        "query": query,
        "type": search_type,
        "format": "json",
        "errorformat": "json",
        "key": key,
    }
    if category:
        params["category"] = category

    req = UrlRequest(f"{VWORLD_SEARCH_URL}?{urlencode(params)}", headers={"User-Agent": "capston-map-search/0.1"})
    try:
        with urlopen(req, timeout=4) as res:
            payload = json.loads(res.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []

    response = payload.get("response") or {}
    if response.get("status") != "OK":
        return []

    result = response.get("result") or {}
    raw_items = result.get("items") or []
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("item") or []
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    items = []
    for raw in raw_items[:size]:
        item = _make_item(raw, search_type, query)
        if item:
            items.append(item)
    return items


def _search_vworld(query: str, limit: int) -> list[dict]:
    calls: list[tuple[str, str | None]] = [
        ("place", None),
        ("address", "road"),
        ("address", "parcel"),
        ("district", "L4"),
        ("road", None),
    ]
    items: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for search_type, category in calls:
        for item in _vworld_request(query, search_type, category=category, size=5):
            key = (item["type"], item["name"], f"{item['lng']:.6f},{item['lat']:.6f}")
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
            if len(items) >= limit:
                return items
    return items


@extend_schema(
    tags=["map"],
    summary="지도 검색",
    description="V-World 검색 API 2.0을 서울 bbox 안에서 조회합니다.",
    parameters=[OpenApiParameter("q", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True)],
)
class SearchView(APIView):
    def get(self, request: Request) -> Response:
        query = str(request.query_params.get("q") or "").strip()
        if len(query) < 2:
            return Response({"items": []}, status=status.HTTP_200_OK)

        cache_key = f"map-search:v2:{query}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        data = {"items": _search_vworld(query, limit=8)}
        cache.set(cache_key, data, timeout=60 * 10)
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(tags=["map"], summary="Transit route placeholder")
class TransitRouteView(APIView):
    def get(self, request: Request) -> Response:
        return Response(
            {
                "status": "unavailable",
                "reason": "PUBLIC_TRANSIT_ROUTE_NOT_IMPLEMENTED",
                "items": [],
                "polyline": None,
                "duration_minutes": None,
            },
            status=status.HTTP_200_OK,
        )
