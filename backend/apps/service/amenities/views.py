from __future__ import annotations

from django.contrib.gis.geos import Polygon
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.caches.map_display.models import MapAmenityMarkerCache

from .models import CATEGORY_CHOICES


ALLOWED_CATEGORIES = tuple(key for key, _label in CATEGORY_CHOICES if key != "etc")
CATEGORY_LIMIT = 1000


def _parse_bbox(raw: str | None) -> tuple[float, float, float, float]:
    if not raw:
        raise ValidationError({"bbox": "bbox is required: minLng,minLat,maxLng,maxLat."})
    try:
        min_lng, min_lat, max_lng, max_lat = [float(part.strip()) for part in raw.split(",")]
    except ValueError as exc:
        raise ValidationError({"bbox": "bbox must be minLng,minLat,maxLng,maxLat."}) from exc
    if min_lng >= max_lng or min_lat >= max_lat:
        raise ValidationError({"bbox": "bbox min values must be smaller than max values."})
    if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180 and -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValidationError({"bbox": "bbox coordinates are out of range."})
    return min_lng, min_lat, max_lng, max_lat


def _parse_categories(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    items = tuple(dict.fromkeys(part.strip() for part in raw.split(",") if part.strip()))
    items = tuple(item for item in items if item != "etc")
    invalid = [item for item in items if item not in ALLOWED_CATEGORIES]
    if invalid:
        raise ValidationError({"categories": f"unknown categories: {invalid}"})
    return items


class AmenityBboxView(APIView):
    def get(self, request: Request) -> Response:
        min_lng, min_lat, max_lng, max_lat = _parse_bbox(request.query_params.get("bbox"))
        categories = _parse_categories(request.query_params.get("categories"))
        selected_categories = categories or ALLOWED_CATEGORIES

        bbox = Polygon.from_bbox((min_lng, min_lat, max_lng, max_lat))
        base_qs = MapAmenityMarkerCache.objects.filter(location__within=bbox)

        items: list[dict] = []
        for category in selected_categories:
            rows = (
                base_qs
                .filter(category=category)
                .order_by("name", "id")[:CATEGORY_LIMIT]
            )
            items.extend(
                {
                    "id": row.id,
                    "category": row.category,
                    "name": row.name,
                    "lat": row.location.y if row.location else None,
                    "lng": row.location.x if row.location else None,
                    "source_table": "",
                    "source_id": "",
                }
                for row in rows
            )

        return Response(
            {
                "bbox": [min_lng, min_lat, max_lng, max_lat],
                "categories": selected_categories,
                "limit": CATEGORY_LIMIT,
                "limit_scope": "category",
                "count": len(items),
                "items": items,
            },
            status=status.HTTP_200_OK,
        )
