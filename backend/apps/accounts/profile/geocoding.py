from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from django.contrib.gis.geos import Point

from apps.accounts.profile.models import UserProfile


def geocode_address(address: str) -> tuple[Point | None, str, str]:
    query = address.strip()
    if not query:
        return None, "not_provided", ""
    key = os.environ.get("V_WORLD_API_KEY", "").strip()
    if not key:
        return None, "failed", "V_WORLD_API_KEY is not configured."
    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": "1",
        "page": "1",
        "query": query,
        "type": "address",
        "category": "road",
        "format": "json",
        "errorformat": "json",
        "key": key,
    }
    try:
        req = UrlRequest(
            f"https://api.vworld.kr/req/search?{urlencode(params)}",
            headers={"User-Agent": "capston-user-address/0.1"},
        )
        with urlopen(req, timeout=4) as res:
            payload = json.loads(res.read().decode("utf-8", errors="replace"))
        response = payload.get("response") or {}
        if response.get("status") != "OK":
            return None, "failed", str(response.get("error") or "address not found")[:255]
        items = ((response.get("result") or {}).get("items") or [])
        if isinstance(items, dict):
            items = [items]
        point = (items[0].get("point") if items else {}) or {}
        lng = float(point.get("x"))
        lat = float(point.get("y"))
        return Point(lng, lat, srid=4326), "success", ""
    except Exception as exc:
        return None, "failed", str(exc)[:255]


def apply_address(profile: UserProfile, address: str | None) -> None:
    cleaned = (address or "").strip()
    profile.address = cleaned
    point, status_value, error = geocode_address(cleaned)
    profile.home_location = point
    profile.address_geocode_status = status_value
    profile.address_geocode_error = error
