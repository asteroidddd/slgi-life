from __future__ import annotations

import csv
import json
from pathlib import Path

from django.core.cache import cache
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public_data.regions.models import Adong, Ldong


DATA_DIR = Path(__file__).resolve().parents[3] / "data"


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
        "score": getattr(current, "score_total", 0.0) if current else 0.0,
        "rank_rent": getattr(current, "rank_rent", None) if current else None,
        "rank_amenity": getattr(current, "rank_amenity", None) if current else None,
        "rank_transit": getattr(current, "rank_transit", None) if current else None,
        "rank_safety": getattr(current, "rank_safety", None) if current else None,
        "rank_total": getattr(current, "rank_total", None) if current else None,
        "lat": region.location.y if getattr(region, "location", None) else None,
        "lng": region.location.x if getattr(region, "location", None) else None,
    }


def _load_adong_geojson_from_data() -> dict:
    with (DATA_DIR / "gu_code.csv").open(encoding="utf-8-sig", newline="") as f:
        gu_rows = list(csv.DictReader(f))
    with (DATA_DIR / "adong_code.csv").open(encoding="utf-8-sig", newline="") as f:
        adong_rows = list(csv.DictReader(f))
    with (DATA_DIR / "gu_boundaries.geojson").open(encoding="utf-8") as f:
        gu_geojson = json.load(f)
    with (DATA_DIR / "adong_boundaries.geojson").open(encoding="utf-8") as f:
        adong_geojson = json.load(f)

    gu_code_by_name = {row["gu_name"]: row["gu_code"] for row in gu_rows}
    gu_name_by_code = {row["gu_code"]: row["gu_name"] for row in gu_rows}
    legacy_gu_to_gu_code: dict[str, str] = {}
    for feature in gu_geojson.get("features", []):
        props = feature.get("properties") or {}
        name = str(props.get("SIGUNGU_NM") or "").strip()
        legacy_code = str(props.get("SIGUNGU_CD") or "").strip()
        if name and legacy_code and name in gu_code_by_name:
            legacy_gu_to_gu_code[legacy_code] = gu_code_by_name[name]

    adong_by_gu_name = {
        (row["gu_code"], row["adong_name"]): row["adong_code"]
        for row in adong_rows
    }

    normalized_features = []
    for feature in adong_geojson.get("features", []):
        props = feature.get("properties") or {}
        legacy_adm_cd = str(props.get("ADM_CD") or "").strip()
        adm_name = str(props.get("ADM_NM") or "").strip()
        gu_code = legacy_gu_to_gu_code.get(legacy_adm_cd[:5], "")
        adong_code = adong_by_gu_name.get((gu_code, adm_name), "")
        if not adong_code:
            continue
        gu_name = gu_name_by_code.get(gu_code, "")
        normalized_features.append(
            {
                "type": "Feature",
                "geometry": feature.get("geometry"),
                "properties": {
                    "adm_nm": f"서울특별시 {gu_name} {adm_name}".strip(),
                    "adm_cd": adong_code[:-3],
                    "adm_cd2": adong_code,
                    "sgg": gu_code,
                    "sido": "11",
                    "sidonm": "서울특별시",
                    "sggnm": gu_name,
                    "ADM_CD": legacy_adm_cd,
                    "ADM_NM": adm_name,
                    "BASE_DATE": props.get("BASE_DATE"),
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "name": "adong_boundaries",
        "features": normalized_features,
    }


def _load_ldong_geojson_from_data() -> dict:
    with (DATA_DIR / "gu_code.csv").open(encoding="utf-8-sig", newline="") as f:
        gu_rows = list(csv.DictReader(f))
    with (DATA_DIR / "ldong_code.csv").open(encoding="utf-8-sig", newline="") as f:
        ldong_rows = list(csv.DictReader(f))
    with (DATA_DIR / "ldong_boundaries.geojson").open(encoding="utf-8") as f:
        ldong_geojson = json.load(f)

    gu_name_by_code = {row["gu_code"]: row["gu_name"] for row in gu_rows}
    ldong_by_code = {row["ldong_code"]: row for row in ldong_rows}

    normalized_features = []
    for feature in ldong_geojson.get("features", []):
        props = feature.get("properties") or {}
        emd_cd = str(props.get("EMD_CD") or "").strip()
        ldong_code = emd_cd if len(emd_cd) == 10 else f"{emd_cd}00"
        row = ldong_by_code.get(ldong_code)
        if not row:
            continue
        gu_code = row["gu_code"]
        gu_name = gu_name_by_code.get(gu_code, "")
        ldong_name = row["ldong_name"]
        normalized_features.append(
            {
                "type": "Feature",
                "geometry": feature.get("geometry"),
                "properties": {
                    "adm_nm": f"서울특별시 {gu_name} {ldong_name}".strip(),
                    "adm_cd": ldong_code[:-2],
                    "adm_cd2": ldong_code,
                    "sgg": gu_code,
                    "sido": "11",
                    "sidonm": "서울특별시",
                    "sggnm": gu_name,
                    "ADM_CD": ldong_code,
                    "ADM_NM": ldong_name,
                    "BASE_DATE": props.get("BASE_DATE"),
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "name": "ldong_boundaries",
        "features": normalized_features,
    }


class HeatmapAdongGeoJsonView(APIView):
    def get(self, request: Request) -> Response:
        cache_key = "heatmap:geojson:adongs:v1"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)
        data = _load_adong_geojson_from_data()
        cache.set(cache_key, data, timeout=60 * 60 * 24)
        return Response(data, status=status.HTTP_200_OK)


class HeatmapLdongGeoJsonView(APIView):
    def get(self, request: Request) -> Response:
        cache_key = "heatmap:geojson:ldongs:v1"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)
        data = _load_ldong_geojson_from_data()
        cache.set(cache_key, data, timeout=60 * 60 * 24)
        return Response(data, status=status.HTTP_200_OK)


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
