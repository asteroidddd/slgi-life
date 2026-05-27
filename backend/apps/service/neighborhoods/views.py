"""
Adong 관련 뷰.

엔드포인트:
- GET /api/adongs/scores?w_rent=33&w_amenity=33&w_transit=34
  → 행정동 종합 점수 리스트 (메인 지도 히트맵용)
- GET /api/adongs/<slug>/summary?w_rent=&w_amenity=&w_transit=
  → 동네 패널용 요약 (SPEC 6.2)
- GET /api/adongs/<slug>/detail?w_rent=&w_amenity=&w_transit=
  → 동네 상세 페이지 (SPEC 6.3)
- GET /api/compare?slugs=A,B,C[&w_rent=&w_amenity=&w_transit=]
  → 동네 비교 (SPEC 6.4, 최대 3개)
- GET /api/adongs/<slug>/population
  → 행정동 인구 시계열 (대시보드 Phase 2)
- GET /api/adongs/<slug>/gu-metrics
  → 소속 구의 최신 지표 + 서울 평균 (대시보드 Phase 2)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.cache import cache
from datetime import date

from .adong_surface import build_adong_qs, wrap
from .compare_dummy import build_compare_row, compute_rent_converted_avgs
from .explore import build_explore_response
from .score_point import compute_point_score
from .serializers import (
    AdongCompareItemSerializer,
    AdongDetailSerializer,
    AdongScoreSerializer,
    AdongSummarySerializer,
    KernelScoreRequestSerializer,
)



DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _load_adong_geojson_from_data() -> dict:
    """backend/data 행정동 경계를 프론트 기존 GeoJSON properties 형식으로 정규화."""
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
    legacy_gu_to_gu_code = {}
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


def _extract_exterior_rings(geometry: dict | None) -> list[list[list[float]]]:
    """GeoJSON Polygon/MultiPolygon에서 외곽 링만 추출."""
    if not geometry:
        return []
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates") or []
    rings: list[list[list[float]]] = []
    if geom_type == "Polygon":
        if coords and coords[0]:
            rings.append(coords[0])
    elif geom_type == "MultiPolygon":
        for polygon in coords:
            if polygon and polygon[0]:
                rings.append(polygon[0])
    return rings


def _load_seoul_mask_geojson_from_data() -> dict:
    """서울 내부를 구멍으로 둔 반전 마스크 GeoJSON."""
    with (DATA_DIR / "gu_boundaries.geojson").open(encoding="utf-8") as f:
        gu_geojson = json.load(f)

    holes: list[list[list[float]]] = []
    for feature in gu_geojson.get("features", []):
        holes.extend(_extract_exterior_rings(feature.get("geometry")))

    # 서울 주변을 충분히 덮는 외곽. 실제 지도는 서울 근방만 쓰므로 세계 전체보다
    # 작은 bbox가 SVG 렌더링 비용과 좌표 왜곡 리스크가 낮다.
    outer = [
        [124.0, 33.0],
        [130.5, 33.0],
        [130.5, 39.5],
        [124.0, 39.5],
        [124.0, 33.0],
    ]

    return {
        "type": "FeatureCollection",
        "name": "seoul_outer_mask",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [outer, *holes],
                },
                "properties": {"name": "서울 외 지역 마스크"},
            }
        ],
    }


@extend_schema(
    tags=["geojson"],
    summary="행정동 경계 GeoJSON",
    description="backend/data/adong_boundaries.geojson을 프론트 히트맵 매칭용 properties로 정규화해 반환합니다.",
)
class AdongGeoJsonView(APIView):
    """GET /api/geojson/adongs — 행정동 경계 GeoJSON."""

    def get(self, request: Request) -> Response:
        cache_key = "geojson:adongs:v1"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)
        data = _load_adong_geojson_from_data()
        cache.set(cache_key, data, timeout=60 * 60 * 24)
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["geojson"],
    summary="서울 외 지역 마스크 GeoJSON",
    description="backend/data/gu_boundaries.geojson을 이용해 서울 내부를 제외한 반투명 마스크용 GeoJSON을 반환합니다.",
)
class SeoulMaskGeoJsonView(APIView):
    """GET /api/geojson/seoul-mask — 서울 외 지역 마스크 GeoJSON."""

    def get(self, request: Request) -> Response:
        cache_key = "geojson:seoul-mask:v1"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)
        data = _load_seoul_mask_geojson_from_data()
        cache.set(cache_key, data, timeout=60 * 60 * 24)
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["schools"],
    summary="학교 선택 목록",
    description="커널 점수/대시보드 학교 선택 UI에서 사용할 실제 Univ DB 기반 학교 목록.",
)
class SchoolOptionsView(APIView):
    """GET /api/schools/options — Univ DB 기반 학교 선택 목록."""

    def get(self, request: Request) -> Response:
        cache_key = "school_options:v1"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        from apps.public_data.univ.models import Univ  # noqa: WPS433

        schools = [
            {
                "id": row["id"],
                "name": row["name"],
                "school_type": row["school_type"],
            }
            for row in Univ.objects.filter(location__isnull=False)
            .order_by("name", "id")
            .values("id", "name", "school_type")
        ]
        data = {"schools": schools}
        cache.set(cache_key, data, timeout=3600)
        return Response(data, status=status.HTTP_200_OK)

# 비교 가능한 최대 동 수 (SPEC 6.4)
COMPARE_MAX_SLUGS = 3

# 기본 가중치 (SPEC 6.1 — 첫 진입 시 33/33/34, 합 100)
DEFAULT_W_RENT = 33
DEFAULT_W_AMENITY = 33
DEFAULT_W_TRANSIT = 34

# 합계 허용 오차 (반올림 누적 대비)
WEIGHT_SUM_TOLERANCE = 1


def _parse_weight(request: Request, key: str, default: int) -> int:
    """쿼리 파라미터에서 정수 가중치(0~100)를 추출. 부정확하면 ValidationError."""
    raw = request.query_params.get(key)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({key: "정수여야 합니다 (0~100)."}) from exc
    if not 0 <= value <= 100:
        raise ValidationError({key: "0~100 범위여야 합니다."})
    return value


def _parse_and_validate_weights(request: Request) -> dict[str, float]:
    """
    AdongScoresView / AdongSummaryView 공통 — 쿼리 파라미터 가중치 파싱·검증.

    반환: {"rent": 0~1, "amenity": 0~1, "transit": 0~1} (정규화된 float)
    오류:
        - 정수가 아니거나 범위 밖 → 400 (필드별 메시지)
        - 합이 100±1을 벗어남 → 400 ("weights" 키)
    """
    w_rent = _parse_weight(request, "w_rent", DEFAULT_W_RENT)
    w_amenity = _parse_weight(request, "w_amenity", DEFAULT_W_AMENITY)
    w_transit = _parse_weight(request, "w_transit", DEFAULT_W_TRANSIT)

    total = w_rent + w_amenity + w_transit
    if abs(total - 100) > WEIGHT_SUM_TOLERANCE:
        raise ValidationError(
            {
                "weights": (
                    f"가중치 합이 100이어야 합니다 (현재 {total}). "
                    "허용 오차는 ±1입니다."
                )
            }
        )

    return {
        "rent": w_rent / 100.0,
        "amenity": w_amenity / 100.0,
        "transit": w_transit / 100.0,
    }


# Swagger에 표시할 가중치 파라미터 공용 정의.
WEIGHT_PARAMS = [
    OpenApiParameter(
        name="w_rent",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        required=False,
        description="전월세 가중치 0~100 (default 33). w_amenity + w_transit과 합 100±1.",
    ),
    OpenApiParameter(
        name="w_amenity",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        required=False,
        description="생활시설 가중치 0~100 (default 33).",
    ),
    OpenApiParameter(
        name="w_transit",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        required=False,
        description="교통 가중치 0~100 (default 34).",
    ),
]


@extend_schema(
    tags=["adongs"],
    summary="행정동 종합 점수 리스트 (메인 지도 히트맵용)",
    description=(
        "서울 425개 행정동의 가중합 종합 점수와 중심점 좌표, raw 축별 점수 3종을 반환. "
        "가중치는 0~100 정수 합 100±1. 응답은 score 내림차순 정렬."
    ),
    parameters=WEIGHT_PARAMS,
)
class AdongScoresView(APIView):
    """
    GET /api/adongs/scores?w_rent=33&w_amenity=33&w_transit=34

    응답: [{slug, name, gu, score, lat, lng, score_rent, score_amenity, score_transit}, ...]
    score는 0~100 범위의 가중합 (소수점 둘째 자리), 내림차순 정렬.
    score_rent/amenity/transit은 raw 점수(SPEC 14.3 클라 재계산용).
    """

    pagination_class = None  # 426개 정도라 한 번에 반환 (SPEC 14.3 클라이언트 캐시)

    def get(self, request: Request) -> Response:
        weights = _parse_and_validate_weights(request)

        # 425개 정도라 단일 쿼리 + 메모리 정렬. 인덱스/공간 쿼리 불필요.
        # 7G-B1: Adong + current_score(LEFT) + Gu 합성. score_rent NULL→0 (결정 1A).
        adongs = build_adong_qs()
        wrapped = [wrap(a) for a in adongs]
        serialized = AdongScoreSerializer(
            wrapped, many=True, context={"weights": weights}
        ).data
        # score 내림차순 정렬 (SPEC 6.1: 사용자가 "어디가 좋은가"를 보기 편함)
        serialized.sort(key=lambda d: d["score"], reverse=True)

        return Response(serialized, status=status.HTTP_200_OK)


@extend_schema(
    tags=["adongs"],
    summary="동네 패널 요약 (SPEC 6.2)",
    description="단일 행정동의 패널용 핵심 지표 5종 + 한 줄 요약.",
    parameters=WEIGHT_PARAMS,
)
class AdongSummaryView(APIView):
    """
    GET /api/adongs/<slug>/summary?w_rent=&w_amenity=&w_transit=

    동네 패널(SPEC 6.2)용 요약. 가중치 파라미터는 옵션이며 default 33/33/34.
    응답: {slug, name, gu, score, summary, rent_avg, nearest_station,
           amenity_level, safety_level}
    """

    def get(self, request: Request, slug: str) -> Response:
        weights = _parse_and_validate_weights(request)

        # 7G-B1: Adong + current_score 조회. DoesNotExist는 Adong 쪽으로 위임.
        from apps.public_data.regions.models import Adong  # noqa: WPS433

        try:
            adong = build_adong_qs().get(slug=slug)
        except Adong.DoesNotExist as exc:
            raise NotFound({"detail": "동을 찾을 수 없습니다."}) from exc

        adong = wrap(adong)
        data = AdongSummarySerializer(adong, context={"weights": weights}).data
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["adongs"],
    summary="동네 상세 — 6개 섹션 (SPEC 6.3)",
    description=(
        "Hero / 부동산 시세 / 편의시설 / 교통 / 자취생 리뷰 / 비슷한 동네를 한 번에 반환. "
        "현재 모두 더미 데이터 (10단계 data-pipeline 적재 후 교체)."
    ),
    parameters=WEIGHT_PARAMS,
)
class AdongDetailView(APIView):
    """
    GET /api/adongs/<slug>/detail?w_rent=&w_amenity=&w_transit=

    동네 상세 페이지(SPEC 6.3)용 전체 데이터. 6개 섹션을 한 번에 반환:
    Hero / RealEstate / Amenities / Transit / Reviews / SimilarAdongs.

    가중치 파라미터는 옵션이며 default 33/33/34. 가중치는 score 필드에만 영향.
    한 줄 요약과 vs_seoul_avg_pct는 raw 점수 기반이므로 가중치와 별개.
    """

    def get(self, request: Request, slug: str) -> Response:
        weights = _parse_and_validate_weights(request)

        # 7G-B1: Adong + current_score 조회. 비슷한 동네 계산은 detail builder가 별도 조회.
        from apps.public_data.regions.models import Adong  # noqa: WPS433

        try:
            adong = build_adong_qs().get(slug=slug)
        except Adong.DoesNotExist as exc:
            raise NotFound({"detail": "동을 찾을 수 없습니다."}) from exc

        adong = wrap(adong)
        data = AdongDetailSerializer(adong, context={"weights": weights}).data
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["compare"],
    summary="동네 비교 (SPEC 6.4, 최대 3개)",
    description="콤마 구분 슬러그 1~3개를 받아 7개 비교 지표를 입력 순서로 반환.",
    parameters=[
        OpenApiParameter(
            name="slugs",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="콤마 구분 슬러그. 예: `1101053,1101054,1101055`",
        ),
        *WEIGHT_PARAMS,
    ],
)
class CompareView(APIView):
    """
    GET /api/compare?slugs=A,B,C[&w_rent=&w_amenity=&w_transit=]

    동네 비교(SPEC 6.4). 최대 3개 슬러그를 받아 7개 비교 지표를 한 번에 반환한다.

    응답: { weights: {...}, adongs: [AdongCompareItem, ...] }
      - weights: 적용된 가중치 (정수 0~100, 합 100±1) — 프론트가 표시용으로 사용
      - adongs: 입력 슬러그 순서 그대로 (프론트가 비교표 컬럼 순서 보존하기 위함)

    오류:
      - slugs 미지정/공백 → 400 ({"slugs": "최소 1개의 슬러그가 필요합니다."})
      - slugs > 3 → 400 ({"slugs": "최대 3개 동네까지 비교할 수 있습니다."})
      - 미존재 슬러그 포함 → 404 ({"detail": "찾을 수 없는 동네: slug_x"})
      - 가중치 검증 실패 → _parse_and_validate_weights가 400 발생
    """

    def get(self, request: Request) -> Response:
        weights = _parse_and_validate_weights(request)

        # ---- slugs 파싱 ----
        raw = request.query_params.get("slugs", "")
        slugs = [s.strip() for s in raw.split(",") if s.strip()]
        if not slugs:
            raise ValidationError({"slugs": "최소 1개의 슬러그가 필요합니다."})
        if len(slugs) > COMPARE_MAX_SLUGS:
            raise ValidationError(
                {"slugs": f"최대 {COMPARE_MAX_SLUGS}개 동네까지 비교할 수 있습니다."}
            )

        # ---- 한 번의 쿼리로 fetch 후 dict 룩업 ----
        # 입력 슬러그 순서 그대로 응답하기 위해 dict로 매핑.
        # 7G-B1: Adong + current_score 합성 후 wrap.
        qs = build_adong_qs().filter(slug__in=slugs)
        by_slug = {a.slug: wrap(a) for a in qs}

        missing = [s for s in slugs if s not in by_slug]
        if missing:
            raise NotFound({"detail": f"찾을 수 없는 동네: {', '.join(missing)}"})

        # 환산월세 평균을 한 번에 사전 계산 (N+1 회피).
        # 같은 구의 RentDeal 만 fetch 하므로 비용 제한적 (5개 구 27,050건 케이스).
        target_dongs = [by_slug[s] for s in slugs]
        rent_converted_map = compute_rent_converted_avgs(target_dongs)

        # 입력 순서 그대로 행 빌드
        rows = [
            build_compare_row(
                by_slug[s],
                weights,
                rent_converted_avg=rent_converted_map.get(s),
            )
            for s in slugs
        ]

        # 응답: 적용 가중치를 정수 % 형태로 함께 반환 (프론트가 표시용으로 사용)
        applied_weights = {
            "w_rent": int(round(weights["rent"] * 100)),
            "w_amenity": int(round(weights["amenity"] * 100)),
            "w_transit": int(round(weights["transit"] * 100)),
        }

        return Response(
            {
                "weights": applied_weights,
                "adongs": AdongCompareItemSerializer(rows, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["adongs"],
    summary="임의 지점 커널 점수 (SPEC 11, Phase 2a)",
    description=(
        "지도 위 임의 클릭 지점(lat/lng)에 대해 가우시안 커널(σ=300m, 1km 컷) "
        "기반의 종합 점수를 계산한다. 내부적으로 amenity 카테고리별 가중합, "
        "가까운 지하철 거리, 1km 버스 정류장 수, 포인트가 속한 행정동의 score_rent "
        "(이미 동 단위 백분위 정규화) 를 조합한다. "
        "school 옵션 지정 시 해당 학교까지의 통학 시간(분, haversine 22km/h)을 함께 반환."
    ),
    request=KernelScoreRequestSerializer,
)
class KernelScoreView(APIView):
    """
    POST /api/score/point

    Request body:
      {
        "lat": 37.5663, "lng": 126.9783,
        "weights": {"rent": 0.3, "amenity": 0.4, "transit": 0.3},
        "school": "동국대"  // optional
      }

    Response:
      {
        "score": 72.4,
        "breakdown": {"rent": 68.2, "amenity": 81.5, "transit": 70.1},
        "nearest": [{category, name, [line], walk_min, distance_m}, ...],
        "radius_counts": {"convenience": 8, "cafe": 12, "hospital": 2, ...},
        "commute_min": 22  // school 미지정 시 null
      }

    오류:
      - lat/lng 범위 벗어남 (한반도 외) → 400
      - weights 음수 또는 모두 0 → 400
      - school 매핑 안 됨 → commute_min: null (오류 아님)
    """

    def post(self, request: Request) -> Response:
        ser = KernelScoreRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        result = compute_point_score(
            lat=data["lat"],
            lng=data["lng"],
            weights=data["weights"],
            school=data.get("school") or None,
        )
        return Response(result, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Phase 4.8 — 자취 시세 BI 대시보드 (`/adong/<slug>/explore`)
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["adongs"],
    summary="자취 시세 BI 대시보드 데이터 (Phase 4.8)",
    description=(
        "한 동의 자취 시장을 깊이 탐색하기 위한 BI 응답. 사용자가 거래유형/기간/"
        "보증금/월세/면적 필터를 자유롭게 조합하면 KPI · 유형별 평균 · 면적-환산"
        "월세 산점도 · 보증금 대역 분포 · 월별 추이 · 페이지네이션된 거래표가 모두 "
        "동기화되어 반환된다. 필터 파라미터/응답 포맷은 backend/apps/neighborhoods/"
        "explore.py 참조."
    ),
    parameters=[
        OpenApiParameter(
            name="deal_types",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="콤마 구분: villa,dagagu,danok,officetel,apt (default 자취 4종)",
        ),
        OpenApiParameter(
            name="period",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="3m | 6m | 12m | 24m | all (default 6m)",
        ),
        OpenApiParameter(
            name="deposit_min",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="만원 (default 0)",
        ),
        OpenApiParameter(
            name="deposit_max",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="만원 (default 50000)",
        ),
        OpenApiParameter(
            name="monthly_min",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="만원 (default 0)",
        ),
        OpenApiParameter(
            name="monthly_max",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="만원 (default 300)",
        ),
        OpenApiParameter(
            name="area_min",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="m² (default 10)",
        ),
        OpenApiParameter(
            name="area_max",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="m² (default 100)",
        ),
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="1-indexed (default 1)",
        ),
        OpenApiParameter(
            name="page_size",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="default 20, max 100",
        ),
        OpenApiParameter(
            name="sort",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                "date_desc | date_asc | deposit_desc | deposit_asc | "
                "monthly_desc | monthly_asc | converted_desc | converted_asc | "
                "area_desc | area_asc (default date_desc)"
            ),
        ),
    ],
)
class AdongExploreView(APIView):
    """GET /api/adongs/<slug>/explore?<filters>"""

    def get(self, request: Request, slug: str) -> Response:
        # 7G-B1: Adong + current_score 합성. explore는 adong.code/gu(string)만 사용 (B2 확인 영역).
        from apps.public_data.regions.models import Adong  # noqa: WPS433

        try:
            adong = build_adong_qs().get(slug=slug)
        except Adong.DoesNotExist as exc:
            raise NotFound({"detail": "동을 찾을 수 없습니다."}) from exc

        adong = wrap(adong)
        data = build_explore_response(adong, request, today=date.today())
        return Response(data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 대시보드 Phase 2 — 인구 시계열 + 구별 지표
# ---------------------------------------------------------------------------

from django.core.cache import cache

from apps.public_data.populations.models import AdongPopulation
from apps.public_data.regions.models import Gu
from apps.public_data.metrics.models import GuMetric, Metric, SeoulMetric


def _get_dong_or_404(slug: str):
    """slug로 Adong(+current_score+Gu)을 조회 후 Adong 인터페이스 호환 wrap 반환. 없으면 404.

    7G-B1: regions.Adong + current_score ??. ?? dict key ?? lock ??.
    """
    from apps.public_data.regions.models import Adong  # noqa: WPS433

    try:
        adong = build_adong_qs().get(slug=slug)
    except Adong.DoesNotExist as exc:
        raise NotFound({"detail": "동을 찾을 수 없습니다."}) from exc
    return wrap(adong)


def _dong_header(adong) -> dict:
    """공통 adong 식별 dict."""
    return {"slug": adong.slug, "name": adong.name, "gu": adong.gu}


@extend_schema(
    tags=["adongs"],
    summary="행정동 인구 시계열 (대시보드 Phase 2)",
    description=(
        "한 행정동의 인구·세대 시계열 전체를 반환한다. "
        "latest는 가장 최근 행, trend는 날짜 오름차순 전체."
    ),
)
class AdongPopulationView(APIView):
    """
    GET /api/adongs/<slug>/population

    응답:
      {
        "adong": { "slug": "...", "name": "...", "gu": "..." },
        "latest": { "date": "...", "total_population": ..., ... },
        "trend": [ { "date": "...", ... }, ... ]
      }
    """

    def get(self, request: Request, slug: str) -> Response:
        adong = _get_dong_or_404(slug)

        cache_key = f"dong_population:{adong.code}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        rows = (
            AdongPopulation.objects
            .filter(adong=adong.code)
            .order_by("date")
            .values("date", "total_population", "household_count",
                    "male_population", "female_population")
        )
        trend = [
            {
                "date": str(r["date"]),
                "total_population": r["total_population"],
                "household_count": r["household_count"],
                "male_population": r["male_population"],
                "female_population": r["female_population"],
            }
            for r in rows
        ]

        latest = trend[-1] if trend else None

        data = {
            "adong": _dong_header(adong),
            "latest": latest,
            "trend": trend,
        }

        cache.set(cache_key, data, timeout=600)  # 10분 TTL
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["adongs"],
    summary="소속 구의 최신 지표 + 서울 평균 + 25구 순위/평균 (대시보드 Phase 2/5)",
    description=(
        "한 행정동이 속한 자치구의 GuMetric을 metric_code별로 가장 최신 1행씩 반환하고, "
        "동일하게 metric_code별 최신 SeoulMetric도 함께 반환한다. "
        "각 metric에는 25개 구 중 본 구의 순위(`rank_in_seoul`), 데이터 보유 구 수(`gu_count`), "
        "산술 평균(`gu_avg`)이 함께 포함된다. `seoul_avg`는 SeoulMetric raw로 "
        "서울시 전체 합/대표값 의미 (25구 산술 평균이 아님 — 비교 시 `gu_avg` 사용)."
    ),
)
class AdongGuMetricsView(APIView):
    """
    GET /api/adongs/<slug>/gu-metrics

    `gu_metric`은 metric_code마다 적재 주기/최신 날짜가 다르다 (예: POP_RESIDENT*는
    월간 ~2026-04, SAFETY_GRADE_*·POP_YOUTH_*는 연간 ~2024-01). 따라서 "구의 가장
    최신 날짜 1개"로 잡으면 그 날짜에 적재된 코드만 응답에 포함되어 다른 코드가
    누락된다. 이를 막기 위해 (gu, metric_code) 단위로 가장 최신 1행씩을 가져온다
    (PostgreSQL `DISTINCT ON (metric_code) ... ORDER BY metric_code, date DESC`).

    응답:
      {
        "adong": { "slug": "...", "name": "...", "gu": "..." },
        "gu_code": "...",
        "gu_name": "중구",
        "metrics": {
          "POP_RESIDENT":     {
            "value": 117760, "date": "2026-04-01",
            "name": "...", "unit": "명",  "category": "인구",
            "rank_in_seoul": 18, "gu_count": 25, "gu_avg": 378271.6
          },
          ...
        },
        "seoul_avg": {
          "POP_RESIDENT":     { "value": 9456789.0, "date": "2026-04-01" },
          ...
        }
      }

    프론트 주의:
    - top-level `date` 필드는 코드별 `date`로 대체됨.
    - `seoul_avg`는 SeoulMetric raw (서울시 전체 합/대표값)임. "25개 구의 평균"은
      `metrics[code].gu_avg`를 사용. (SeoulMetric은 의미가 다름 — 라이브 검증 결과
      합계/대표값이라 25개 구 산술 평균과 일치하지 않음.)
    - `metrics[code].rank_in_seoul`: 같은 date 기준 25개 구 중 값이 큰 순으로 1위.
      value=null인 구는 제외하고 rank 부여. 해당 구 value=null이면 null.
    - `metrics[code].gu_count`: 그 date에 데이터를 가진 구 수 (값 null 제외).

    캐시는 (구 단위) 5분 TTL. 응답 모양이 바뀌어 캐시 키 v2 로 갱신.
    """

    def get(self, request: Request, slug: str) -> Response:
        adong = _get_dong_or_404(slug)

        # Adong.gu는 CharField (예: "중구"). Gu.name도 동일 값.
        gu = Gu.objects.filter(name=adong.gu).first()
        if gu is None:
            raise NotFound({"detail": f"구를 찾을 수 없습니다: {adong.gu}"})

        # v2: 응답 모양 변경 (rank_in_seoul/gu_count/gu_avg 추가)
        cache_key = f"dong_gu_metrics:v2:{gu.gu_code}"
        cached = cache.get(cache_key)
        if cached is not None:
            # cached 데이터에 adong 헤더만 교체 (같은 구의 다른 동에서도 재사용)
            result = {**cached, "adong": _dong_header(adong)}
            return Response(result, status=status.HTTP_200_OK)

        # 메트릭 메타 사전 로드 (35행)
        metric_meta = {
            m.metric_code: m
            for m in Metric.objects.all()
        }

        # (gu, metric_code)별 최신 1행씩 — PostgreSQL DISTINCT ON.
        # ORDER BY metric_code, -date 가 DISTINCT ON 컬럼과 정확히 매칭되어야 한다.
        gu_rows = list(
            GuMetric.objects
            .filter(gu=gu)
            .order_by("metric_id", "-date")
            .distinct("metric_id")
            .values("metric_id", "date", "value")
        )

        # 본 구의 (metric_code, date) 쌍을 모아서, 같은 (metric_code, date)에 대해
        # 25개 구의 값을 한 번에 fetch → rank/gu_avg 계산.
        # date가 None인 행은 비교 무의미하므로 제외.
        pairs = [
            (r["metric_id"], r["date"])
            for r in gu_rows
            if r["date"] is not None
        ]

        # 25개 구 × ~35 metric ≒ 875행 정도. 단일 쿼리로 처리.
        # metric_id, date IN 조합 — PostgreSQL은 IN 튜플도 지원하지만 ORM 표현이
        # 까다로워, metric_id IN + date IN 조합으로 over-fetch 후 in-memory 필터.
        # 코드별 date가 코드마다 다른 한 over-fetch는 코드 수 × date 수 ≒ 작음.
        if pairs:
            metric_ids = sorted({mid for mid, _d in pairs})
            dates = sorted({d for _mid, d in pairs})
            all_rows = (
                GuMetric.objects
                .filter(metric_id__in=metric_ids, date__in=dates)
                .values("metric_id", "date", "gu_id", "value")
            )
            # peers[(metric_id, date)] = [(gu_id, value_float_or_None), ...]
            peers: dict[tuple, list] = {}
            for r in all_rows:
                key = (r["metric_id"], r["date"])
                v = float(r["value"]) if r["value"] is not None else None
                peers.setdefault(key, []).append((r["gu_id"], v))
        else:
            peers = {}

        metrics_dict = {}
        for row in gu_rows:
            mc = row["metric_id"]
            meta = metric_meta.get(mc)
            v_float = float(row["value"]) if row["value"] is not None else None
            d_str = str(row["date"]) if row["date"] is not None else None

            rank_in_seoul = None
            gu_count = 0
            gu_avg = None
            if row["date"] is not None:
                same_day = peers.get((mc, row["date"]), [])
                non_null_values = [v for (_g, v) in same_day if v is not None]
                gu_count = len(non_null_values)
                if non_null_values:
                    gu_avg = sum(non_null_values) / gu_count
                if v_float is not None and non_null_values:
                    # 값이 큰 순으로 1위. 동률은 동일 rank 부여 (1, 2, 2, 4 식).
                    rank_in_seoul = 1 + sum(
                        1 for x in non_null_values if x > v_float
                    )

            metrics_dict[mc] = {
                "value": v_float,
                "date": d_str,
                "name": meta.name if meta else mc,
                "unit": meta.unit if meta else "",
                "category": meta.category if meta else "",
                "rank_in_seoul": rank_in_seoul,
                "gu_count": gu_count,
                "gu_avg": gu_avg,
            }

        # SeoulMetric — metric_code별 최신 1행씩 (서울시 전체 합/대표값. 의미 주의)
        seoul_rows = (
            SeoulMetric.objects
            .order_by("metric_id", "-date")
            .distinct("metric_id")
            .values("metric_id", "date", "value")
        )
        seoul_avg = {}
        for row in seoul_rows:
            seoul_avg[row["metric_id"]] = {
                "value": float(row["value"]) if row["value"] is not None else None,
                "date": str(row["date"]) if row["date"] is not None else None,
            }

        cacheable = {
            "gu_code": gu.gu_code,
            "gu_name": gu.name,
            "metrics": metrics_dict,
            "seoul_avg": seoul_avg,
        }
        cache.set(cache_key, cacheable, timeout=300)  # 5분 TTL

        data = {**cacheable, "adong": _dong_header(adong)}
        return Response(data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 대시보드 Phase 4 — 구별 지표 시계열 (추이 차트용)
# ---------------------------------------------------------------------------

# 시계열 endpoint 파라미터 상한
SERIES_MAX_CODES = 10
SERIES_MIN_YEARS = 1
SERIES_MAX_YEARS = 20
SERIES_DEFAULT_YEARS = 10


def _parse_series_params(request: Request) -> tuple[list[str], int]:
    """
    /gu-metrics/series 전용 파라미터 파싱·검증.

    반환: (codes, years)
    오류:
      - codes 없거나 빈 문자열 → 400
      - codes 11개 이상 → 400
      - years 정수 변환 실패 → 400
      - years 범위 밖 (1~20) → 400
    """
    raw_codes = request.query_params.get("codes", "")
    codes = [c.strip() for c in raw_codes.split(",") if c.strip()]
    if not codes:
        raise ValidationError({"codes": "최소 1개의 metric_code가 필요합니다."})
    if len(codes) > SERIES_MAX_CODES:
        raise ValidationError(
            {"codes": f"최대 {SERIES_MAX_CODES}개까지 지원합니다 (현재 {len(codes)})."}
        )
    # 중복 제거 (순서 유지)
    seen: set[str] = set()
    deduped: list[str] = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    raw_years = request.query_params.get("years")
    if raw_years is None:
        years = SERIES_DEFAULT_YEARS
    else:
        try:
            years = int(raw_years)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"years": "정수여야 합니다 (1~20)."}) from exc
        if not SERIES_MIN_YEARS <= years <= SERIES_MAX_YEARS:
            raise ValidationError(
                {"years": f"{SERIES_MIN_YEARS}~{SERIES_MAX_YEARS} 범위여야 합니다."}
            )

    return deduped, years


@extend_schema(
    tags=["adongs"],
    summary="구별 지표 시계열 + 25구 평균선 (대시보드 추이 위젯용)",
    description=(
        "한 행정동이 속한 자치구의 GuMetric을 metric_code별 시계열로 반환한다. "
        "교통사고 추이, 화재 발생 추이, 지가 변동률 시계열 등 추이가 필요한 위젯용. "
        "단일 값(최신 1행)이 필요한 경우 `/gu-metrics`를 사용한다. "
        "`codes`는 콤마 구분, 1~10개. `years`는 최근 N년 (default 10, 1~20). "
        "응답에는 본 구 시계열(`series`)과 함께 25개 구 산술 평균 시계열"
        "(`gu_avg_series`), 가장 최신 시점의 25구 중 순위(`series[code].current_rank`)가 "
        "포함된다. `seoul_series`는 SeoulMetric raw 그대로 (서울시 전체 합/대표값)."
    ),
    parameters=[
        OpenApiParameter(
            name="codes",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="콤마 구분 metric_code 1~10개. 예: `ACC_TOTAL_COUNT,FIRE_COUNT`",
        ),
        OpenApiParameter(
            name="years",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="최근 N년치 (default 10, 1~20).",
        ),
    ],
)
class AdongGuMetricsSeriesView(APIView):
    """
    GET /api/adongs/<slug>/gu-metrics/series?codes=...&years=10

    응답:
      {
        "adong": { "slug": "...", "name": "...", "gu": "..." },
        "gu_code": "...",
        "gu_name": "중구",
        "series": {
          "ACC_TOTAL_COUNT": {
            "name": "교통사고 총 발생건수",
            "unit": "건",
            "category": "교통",
            "points": [ { "date": "2020-01-01", "value": 850.0 }, ... ],
            "current_rank": {
              "rank": 18,
              "total": 25,
              "value": 824.0,
              "date": "2024-01-01"
            }
          },
          ...
        },
        "seoul_series": {
          "ACC_TOTAL_COUNT": { "points": [...] },
          ...
        },
        "gu_avg_series": {
          "ACC_TOTAL_COUNT": {
            "points": [ { "date": "2020-01-01", "value": 1092.4 }, ... ]
          },
          ...
        }
      }

    - 요청한 codes 모두가 응답에 포함된다 (데이터 없으면 points: []).
    - points는 date 오름차순. value가 null이면 그대로 노출 (프론트 connectNulls).
    - `current_rank`는 시계열 가장 최신 date 기준 25구 중 본 구의 순위 (값 큰 순 1위).
      해당 date에 본 구 데이터가 없거나 series가 비면 null.
    - `gu_avg_series`는 date별 25개 구 산술 평균. value=null인 구는 평균에서 제외.
      `seoul_series` (SeoulMetric raw = 서울시 전체 합/대표값)와는 의미가 다름.
    - 캐시는 구 단위 5분 TTL. 응답 모양 변경으로 캐시 키 v2.
    """

    def get(self, request: Request, slug: str) -> Response:
        adong = _get_dong_or_404(slug)
        codes, years = _parse_series_params(request)

        gu = Gu.objects.filter(name=adong.gu).first()
        if gu is None:
            raise NotFound({"detail": f"구를 찾을 수 없습니다: {adong.gu}"})

        # 캐시 키: (구, codes, years) 단위. codes는 정렬해서 키 안정화.
        # v2: 응답에 current_rank / gu_avg_series 추가됨.
        codes_joined = ",".join(sorted(codes))
        cache_key = f"dong_gu_metrics_series:v2:{gu.gu_code}:{codes_joined}:{years}"
        cached = cache.get(cache_key)
        if cached is not None:
            result = {**cached, "adong": _dong_header(adong)}
            return Response(result, status=status.HTTP_200_OK)

        # cutoff: 오늘 기준 N년 전 1월 1일 (연 단위 적재 metric에서도 경계 포함)
        today = date.today()
        cutoff = date(today.year - years, 1, 1)

        # 메트릭 메타 사전 로드 (요청 codes 한정)
        metric_meta = {
            m.metric_code: m
            for m in Metric.objects.filter(metric_code__in=codes)
        }

        # 본 구의 시계열 — (metric_code, date) 오름차순
        gu_rows = (
            GuMetric.objects
            .filter(gu=gu, metric_id__in=codes, date__gte=cutoff)
            .order_by("metric_id", "date")
            .values("metric_id", "date", "value")
        )
        # 모든 요청 코드를 키로 미리 생성 (빈 데이터도 points: [])
        series: dict[str, dict] = {}
        for code in codes:
            meta = metric_meta.get(code)
            series[code] = {
                "name": meta.name if meta else code,
                "unit": meta.unit if meta else "",
                "category": meta.category if meta else "",
                "points": [],
                "current_rank": None,
            }
        for row in gu_rows:
            code = row["metric_id"]
            entry = series.get(code)
            if entry is None:
                # 요청 codes에 없는 결과는 무시 (이론상 안 옴)
                continue
            entry["points"].append({
                "date": str(row["date"]) if row["date"] is not None else None,
                "value": float(row["value"]) if row["value"] is not None else None,
            })

        # 25개 구 전체 시계열 (gu_avg_series + current_rank 계산용).
        # 25 구 × 코드 수 × 연 단위 ~10년 ≒ 수천 행. 단일 쿼리.
        all_rows = (
            GuMetric.objects
            .filter(metric_id__in=codes, date__gte=cutoff)
            .values("metric_id", "date", "gu_id", "value")
        )
        # bucket[code][date] = [value, ...]  (null 제외)
        # bucket_with_gu[code][date] = {gu_id: value}  (null 제외, rank 산출용)
        bucket: dict[str, dict] = {code: {} for code in codes}
        bucket_with_gu: dict[str, dict] = {code: {} for code in codes}
        for r in all_rows:
            code = r["metric_id"]
            if code not in bucket:
                continue
            v = r["value"]
            if v is None:
                continue
            vf = float(v)
            d = r["date"]
            bucket[code].setdefault(d, []).append(vf)
            bucket_with_gu[code].setdefault(d, {})[r["gu_id"]] = vf

        gu_avg_series: dict[str, dict] = {code: {"points": []} for code in codes}
        for code in codes:
            by_date = bucket[code]
            for d in sorted(by_date.keys()):
                vals = by_date[d]
                if not vals:
                    continue
                gu_avg_series[code]["points"].append({
                    "date": str(d),
                    "value": sum(vals) / len(vals),
                })

        # current_rank — 본 구의 가장 최신 point 기준
        for code in codes:
            points = series[code]["points"]
            # 가장 최신 non-null point 찾기
            latest_idx = None
            for i in range(len(points) - 1, -1, -1):
                if points[i]["value"] is not None and points[i]["date"] is not None:
                    latest_idx = i
                    break
            if latest_idx is None:
                continue
            latest = points[latest_idx]
            # latest["date"]는 문자열 — bucket key는 date 객체. 매칭 위해 변환.
            try:
                latest_date_obj = date.fromisoformat(latest["date"])
            except (TypeError, ValueError):
                continue
            peers = bucket[code].get(latest_date_obj, [])
            if not peers:
                continue
            v = float(latest["value"])
            rank = 1 + sum(1 for x in peers if x > v)
            series[code]["current_rank"] = {
                "rank": rank,
                "total": len(peers),
                "value": v,
                "date": latest["date"],
            }

        # 서울 시계열 — SeoulMetric raw (서울시 전체 합/대표값).
        seoul_rows = (
            SeoulMetric.objects
            .filter(metric_id__in=codes, date__gte=cutoff)
            .order_by("metric_id", "date")
            .values("metric_id", "date", "value")
        )
        seoul_series: dict[str, dict] = {code: {"points": []} for code in codes}
        for row in seoul_rows:
            code = row["metric_id"]
            entry = seoul_series.get(code)
            if entry is None:
                continue
            entry["points"].append({
                "date": str(row["date"]) if row["date"] is not None else None,
                "value": float(row["value"]) if row["value"] is not None else None,
            })

        cacheable = {
            "gu_code": gu.gu_code,
            "gu_name": gu.name,
            "series": series,
            "seoul_series": seoul_series,
            "gu_avg_series": gu_avg_series,
        }
        cache.set(cache_key, cacheable, timeout=300)  # 5분 TTL

        data = {**cacheable, "adong": _dong_header(adong)}
        return Response(data, status=status.HTTP_200_OK)
