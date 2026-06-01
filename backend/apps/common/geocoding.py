from __future__ import annotations

import json
import math
import os
import socket
import time as sleep_time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.contrib.gis.geos import Point


KAKAO_ADDRESS_URL = "https://dapi.kakao.com/v2/local/search/address.json"
VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"


@dataclass(frozen=True)
class GeocodeResult:
    status: str
    point: Point | None = None
    provider: str | None = None
    address_name: str | None = None
    error: str | None = None


def _optional_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def has_geocoding_key() -> bool:
    return bool(_optional_env("KAKAO_REST_API_KEY", "KAKAO_API_KEY") or _optional_env("V_WORLD_API_KEY", "VWORLD_API_KEY"))


def _point(lng: Any, lat: Any) -> Point | None:
    try:
        lng_float = float(lng)
        lat_float = float(lat)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lng_float) and math.isfinite(lat_float)):
        return None
    if not (-180 <= lng_float <= 180 and -90 <= lat_float <= 90):
        return None
    return Point(lng_float, lat_float, srid=4326)


def _request_json(
    url: str,
    params: dict[str, str],
    *,
    headers: dict[str, str] | None,
    timeout: float,
    interval: float,
    user_agent: str,
) -> dict[str, Any]:
    if interval:
        sleep_time.sleep(interval)
    request_headers = {"User-Agent": user_agent}
    if headers:
        request_headers.update(headers)
    req = Request(f"{url}?{urlencode(params, safe='%')}", headers=request_headers)
    with urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8", errors="replace"))


def _geocode_kakao(
    query: str,
    *,
    request_timeout: float,
    request_interval: float,
    user_agent: str,
) -> GeocodeResult:
    api_key = _optional_env("KAKAO_REST_API_KEY", "KAKAO_API_KEY")
    if not api_key:
        return GeocodeResult(status="failed", provider="kakao", error="KAKAO_REST_API_KEY is not configured.")
    try:
        payload = _request_json(
            KAKAO_ADDRESS_URL,
            {"query": query},
            headers={"Authorization": f"KakaoAK {api_key}"},
            timeout=request_timeout,
            interval=request_interval,
            user_agent=user_agent,
        )
    except HTTPError as exc:
        return GeocodeResult(status="failed", provider="kakao", error=f"HTTP {exc.code}")
    except (URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
        return GeocodeResult(status="failed", provider="kakao", error=f"{type(exc).__name__}: {exc}")

    documents = payload.get("documents") or []
    if isinstance(documents, dict):
        documents = [documents]
    for document in documents:
        point = _point(document.get("x"), document.get("y"))
        if point:
            address_name = str(document.get("address_name") or query).strip()
            return GeocodeResult(status="success", point=point, provider="kakao", address_name=address_name)
    return GeocodeResult(status="failed", provider="kakao", error="address not found")


def _normalize_vworld_items(raw_items: Any) -> list[dict[str, Any]]:
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("item") or []
    if isinstance(raw_items, dict):
        raw_items = [raw_items]
    return raw_items if isinstance(raw_items, list) else []


def _geocode_vworld(
    query: str,
    *,
    categories: tuple[str, ...],
    request_timeout: float,
    request_interval: float,
    user_agent: str,
) -> GeocodeResult:
    api_key = _optional_env("V_WORLD_API_KEY", "VWORLD_API_KEY")
    if not api_key:
        return GeocodeResult(status="failed", provider="vworld", error="V_WORLD_API_KEY is not configured.")

    last_error = "address not found"
    for category in categories:
        try:
            payload = _request_json(
                VWORLD_SEARCH_URL,
                {
                    "service": "search",
                    "request": "search",
                    "version": "2.0",
                    "crs": "EPSG:4326",
                    "size": "1",
                    "page": "1",
                    "query": query,
                    "type": "address",
                    "category": category,
                    "format": "json",
                    "errorformat": "json",
                    "key": api_key,
                },
                headers=None,
                timeout=request_timeout,
                interval=request_interval,
                user_agent=user_agent,
            )
        except HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            continue
        except (URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            continue

        response = payload.get("response") or {}
        if response.get("status") != "OK":
            last_error = str(response.get("error") or "address not found")
            continue

        result = response.get("result") or {}
        for item in _normalize_vworld_items(result.get("items") or []):
            point_raw = item.get("point") or {}
            point = _point(point_raw.get("x"), point_raw.get("y"))
            if not point:
                last_error = "invalid geocode point"
                continue
            address_raw = item.get("address") or {}
            address_name = str(address_raw.get("road") or address_raw.get("parcel") or query).strip()
            return GeocodeResult(status="success", point=point, provider="vworld", address_name=address_name)

    return GeocodeResult(status="failed", provider="vworld", error=last_error)


def geocode_address(
    query: str,
    *,
    categories: tuple[str, ...] = ("road", "parcel"),
    request_timeout: float = 4.0,
    request_interval: float = 0.0,
    user_agent: str = "capston-geocoder/0.1",
    prefer_kakao: bool = True,
) -> GeocodeResult:
    query = query.strip()
    if not query:
        return GeocodeResult(status="failed", error="address is empty")

    errors: list[str] = []
    if prefer_kakao:
        kakao = _geocode_kakao(
            query,
            request_timeout=request_timeout,
            request_interval=request_interval,
            user_agent=user_agent,
        )
        if kakao.status == "success":
            return kakao
        errors.append(f"kakao: {kakao.error or 'failed'}")

    vworld = _geocode_vworld(
        query,
        categories=categories,
        request_timeout=request_timeout,
        request_interval=request_interval,
        user_agent=user_agent,
    )
    if vworld.status == "success":
        return vworld
    errors.append(f"vworld: {vworld.error or 'failed'}")

    return GeocodeResult(status="failed", error="; ".join(errors)[:255])
