from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request as DRFRequest
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public_data.regions.models import Adong, Ldong


@dataclass(frozen=True)
class SafetyWmsLayer:
    key: str
    name: str
    int_id: str
    url: str
    layers: str
    styles: str


CRIME_ZONE_LAYER = SafetyWmsLayer(
    key="crime_zone",
    name="범죄주의구간",
    int_id="IF_0087",
    url="https://www.safemap.go.kr/openapi2/IF_0087_WMS",
    layers="A2SM_CRMNLHSPOT_TOT",
    styles="A2SM_CrmnlHspot_Tot_Tot",
)

DEFAULT_SRS = "EPSG:4326"
DEFAULT_FORMAT = "image/png"
DEFAULT_TRANSPARENT = "TRUE"
MAX_IMAGE_SIZE = 2048


def _service_key() -> str:
    for name in ("LIFE_INFO_API_KEY", "SAFEMAP_API_KEY", "PUBLIC_DATA_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _parse_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    try:
        min_lng, min_lat, max_lng, max_lat = [float(part.strip()) for part in raw.split(",")]
    except ValueError as exc:
        raise ValidationError({"bbox": "bbox must be minLng,minLat,maxLng,maxLat."}) from exc
    if min_lng >= max_lng or min_lat >= max_lat:
        raise ValidationError({"bbox": "bbox min values must be smaller than max values."})
    if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180 and -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValidationError({"bbox": "bbox coordinates are out of range."})
    return min_lng, min_lat, max_lng, max_lat


def _parse_image_size(raw: str | None, *, field: str) -> int:
    if raw in (None, ""):
        return 512
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValidationError({field: f"{field} must be an integer."}) from exc
    if value < 1 or value > MAX_IMAGE_SIZE:
        raise ValidationError({field: f"{field} must be between 1 and {MAX_IMAGE_SIZE}."})
    return value


def _parse_format(raw: str | None) -> str:
    value = (raw or DEFAULT_FORMAT).strip().lower()
    if value not in {"image/png", "image/jpeg"}:
        raise ValidationError({"format": "format must be image/png or image/jpeg."})
    return value


def _parse_transparent(raw: str | None) -> str:
    value = (raw or DEFAULT_TRANSPARENT).strip().upper()
    if value not in {"TRUE", "FALSE"}:
        raise ValidationError({"transparent": "transparent must be TRUE or FALSE."})
    return value


def _empty_svg(*, width: int, height: int) -> HttpResponse:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="transparent"/>
</svg>"""
    return HttpResponse(svg.encode("utf-8"), content_type="image/svg+xml", status=200)


def _bbox_from_region(request: DRFRequest) -> tuple[dict[str, object] | None, tuple[float, float, float, float] | None]:
    region_type = request.query_params.get("region_type") or request.query_params.get("type")
    slug = request.query_params.get("slug")
    if not (region_type and slug):
        return None, None

    if region_type == "adong":
        region = get_object_or_404(Adong.objects.select_related("gu"), slug=slug)
        code = region.adong_code
    elif region_type == "ldong":
        region = get_object_or_404(Ldong.objects.select_related("gu"), slug=slug)
        code = region.ldong_code
    else:
        raise ValidationError({"region_type": "region_type must be adong or ldong."})

    bbox = tuple(float(value) for value in region.boundary.extent) if region.boundary else None
    return (
        {
            "type": region_type,
            "code": code,
            "slug": region.slug or "",
            "gu_name": region.gu.name,
            "dong_name": region.name,
            "bbox": list(bbox) if bbox else None,
        },
        bbox,
    )


def _layer_payload(layer: SafetyWmsLayer, request: DRFRequest, region: dict[str, object] | None) -> dict[str, object]:
    return {
        "key": layer.key,
        "name": layer.name,
        "source": "safemap",
        "int_id": layer.int_id,
        "wms_url": layer.url,
        "proxy_url": request.build_absolute_uri(request.path),
        "service_key_exposed": False,
        "params": {
            "layers": layer.layers,
            "styles": layer.styles,
            "srs": DEFAULT_SRS,
            "format": DEFAULT_FORMAT,
            "transparent": True,
        },
        "region": region,
    }


def _should_proxy_image(request: DRFRequest) -> bool:
    return any(key in request.query_params for key in ("bbox", "width", "height", "format", "transparent", "srs"))


def _proxy_wms(layer: SafetyWmsLayer, request: DRFRequest, bbox: tuple[float, float, float, float] | None) -> HttpResponse:
    service_key = _service_key()
    if not service_key:
        raise ValidationError({"serviceKey": "SafeMap service key is not configured."})
    if bbox is None:
        raise ValidationError({"bbox": "bbox is required for WMS image proxy."})

    image_format = _parse_format(request.query_params.get("format"))
    width = _parse_image_size(request.query_params.get("width"), field="width")
    height = _parse_image_size(request.query_params.get("height"), field="height")
    params = {
        "serviceKey": service_key,
        "srs": request.query_params.get("srs") or DEFAULT_SRS,
        "bbox": ",".join(str(value) for value in bbox),
        "format": image_format,
        "width": str(width),
        "height": str(height),
        "transparent": _parse_transparent(request.query_params.get("transparent")),
        "layers": layer.layers,
        "styles": layer.styles,
    }
    req = Request(
        f"{layer.url}?{urlencode(params, safe='%')}",
        headers={"User-Agent": "capston-dashboard-safety-wms/0.1"},
    )
    try:
        with urlopen(req, timeout=20) as res:
            content_type = res.headers.get("Content-Type") or image_format
            return HttpResponse(res.read(), content_type=content_type, status=res.status)
    except HTTPError as exc:
        content_type = exc.headers.get("Content-Type", "")
        body = exc.read()
        if "image/" in content_type:
            return HttpResponse(body, content_type=content_type, status=exc.code)
        return _empty_svg(width=width, height=height)
    except (URLError, TimeoutError, socket.timeout):
        return _empty_svg(width=width, height=height)


class SafetyWmsView(APIView):
    layer: SafetyWmsLayer

    def get(self, request: DRFRequest) -> Response | HttpResponse:
        region, region_bbox = _bbox_from_region(request)
        raw_bbox = _parse_bbox(request.query_params.get("bbox"))
        bbox = raw_bbox or region_bbox
        if _should_proxy_image(request):
            return _proxy_wms(self.layer, request, bbox)
        return Response(_layer_payload(self.layer, request, region), status=status.HTTP_200_OK)


class CrimeZoneWmsView(SafetyWmsView):
    layer = CRIME_ZONE_LAYER
