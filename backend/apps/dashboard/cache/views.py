from __future__ import annotations

from copy import deepcopy

from django.contrib.gis.geos import Point
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.cache.models import DashboardAdongCache, DashboardLdongCache
from apps.public_data.regions.models import Adong, Ldong


def _cache_model(region_type: str):
    if region_type == "adong":
        return DashboardAdongCache
    if region_type == "ldong":
        return DashboardLdongCache
    raise ValidationError({"region_type": "region_type must be adong or ldong."})


def _cache_for(region_type: str, slug: str):
    model = _cache_model(region_type)
    relation = "adong" if region_type == "adong" else "ldong"
    return get_object_or_404(model.objects.select_related(relation), **{f"{relation}__slug": slug})


def _intro_payload(cache) -> dict:
    payload = cache.dashboard_payload or {}
    region = payload.get("region") or cache.region_payload
    return {**region, "intro": payload.get("intro") or cache.intro}


def _dashboard_payload(cache, region_type: str) -> dict:
    return deepcopy(cache.dashboard_payload or {})

def _parse_coordinate(value: str | None, *, field: str, minimum: float, maximum: float) -> float:
    if value in (None, ""):
        raise ValidationError({field: f"{field} is required."})
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValidationError({field: f"{field} must be a number."}) from exc
    if parsed < minimum or parsed > maximum:
        raise ValidationError({field: f"{field} is out of range."})
    return parsed


class DashboardCacheView(APIView):
    def get(self, request) -> Response:
        region_type = request.query_params.get("region_type") or request.query_params.get("type")
        slug = request.query_params.get("slug")
        if not region_type:
            raise ValidationError({"region_type": "region_type is required."})
        if not slug:
            raise ValidationError({"slug": "slug is required."})
        cache = _cache_for(region_type, slug)
        return Response(_dashboard_payload(cache, region_type), status=status.HTTP_200_OK)


class RegionIntroView(APIView):
    region_type: str

    def get(self, _request, slug: str) -> Response:
        cache = _cache_for(self.region_type, slug)
        return Response(_intro_payload(cache), status=status.HTTP_200_OK)


class AdongIntroView(RegionIntroView):
    region_type = "adong"


class LdongIntroView(RegionIntroView):
    region_type = "ldong"


class RegionLookupView(APIView):
    region_type: str

    def get(self, request) -> Response:
        lat = _parse_coordinate(request.query_params.get("lat"), field="lat", minimum=-90, maximum=90)
        lng = _parse_coordinate(request.query_params.get("lng"), field="lng", minimum=-180, maximum=180)
        point = Point(lng, lat, srid=4326)
        if self.region_type == "adong":
            region = (
                Adong.objects.select_related("gu")
                .filter(boundary__contains=point)
                .order_by("gu__name", "name")
                .first()
            )
            if not region:
                return Response({"detail": "No administrative dong contains this point."}, status=status.HTTP_404_NOT_FOUND)
            cache = DashboardAdongCache.objects.filter(adong=region).first()
        else:
            region = (
                Ldong.objects.select_related("gu")
                .filter(boundary__contains=point)
                .order_by("gu__name", "name")
                .first()
            )
            if not region:
                return Response({"detail": "No legal dong contains this point."}, status=status.HTTP_404_NOT_FOUND)
            cache = DashboardLdongCache.objects.filter(ldong=region).first()
        if cache:
            return Response(_intro_payload(cache), status=status.HTTP_200_OK)
        return Response(
            {
                "type": self.region_type,
                "code": region.adong_code if self.region_type == "adong" else region.ldong_code,
                "slug": region.slug or "",
                "gu_name": region.gu.name,
                "dong_name": region.name,
                "intro": "",
            },
            status=status.HTTP_200_OK,
        )


class AdongLookupView(RegionLookupView):
    region_type = "adong"


class LdongLookupView(RegionLookupView):
    region_type = "ldong"
