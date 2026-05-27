from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public_data.regions.models import Adong, Ldong


def _current_payload(region, current) -> dict:
    return {
        "code": getattr(region, "adong_code", None) or getattr(region, "ldong_code", None),
        "slug": getattr(region, "slug", ""),
        "name": region.name,
        "gu": region.gu.name if getattr(region, "gu", None) else "",
        "score_rent": getattr(current, "score_rent", None),
        "score_amenity": getattr(current, "score_amenity", 0.0) if current else 0.0,
        "score_transit": getattr(current, "score_transit", 0.0) if current else 0.0,
        "score_safety": getattr(current, "score_safety", 0.0) if current else 0.0,
        "score_total": getattr(current, "score_total", 0.0) if current else 0.0,
        "rank_rent": getattr(current, "rank_rent", None) if current else None,
        "rank_amenity": getattr(current, "rank_amenity", None) if current else None,
        "rank_transit": getattr(current, "rank_transit", None) if current else None,
        "rank_safety": getattr(current, "rank_safety", None) if current else None,
        "rank_total": getattr(current, "rank_total", None) if current else None,
        "lat": region.location.y if getattr(region, "location", None) else None,
        "lng": region.location.x if getattr(region, "location", None) else None,
    }


class HeatmapAdongScoresView(APIView):
    def get(self, request):
        rows = [
            _current_payload(row, getattr(row, "current_score", None))
            for row in Adong.objects.select_related("gu", "current_score").all()
        ]
        rows.sort(key=lambda item: item["score_total"], reverse=True)
        return Response(rows, status=status.HTTP_200_OK)


class HeatmapLdongScoresView(APIView):
    def get(self, request):
        rows = [
            _current_payload(row, getattr(row, "current_score", None))
            for row in Ldong.objects.select_related("gu", "current_score").all()
        ]
        rows.sort(key=lambda item: item["score_total"], reverse=True)
        return Response(rows, status=status.HTTP_200_OK)
