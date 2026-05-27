"""
RentDeal 관련 뷰.

엔드포인트:
- GET /api/transactions/bbox?bbox=lng1,lat1,lng2,lat2
                            &deal_type=apt|officetel|villa|dagagu|danok|all
                            &from=YYYY-MM-DD&to=YYYY-MM-DD
                            &limit=200
  → 메인 지도 bbox 내 실거래 핀 (SPEC 6.1)
sub-plan 4.5B 정합:
- 컬럼명 변경: deal_date → contract_date, build_year → construction_year.
- deal_type 영문 enum 컬럼 제거 → housing_type 한글 raw 단일.
  쿼리 파라미터/응답 dict 'deal_type'은 영문 enum 그대로 보존 (frontend lock 1).
  → DEAL_TYPE_TO_HOUSING_TYPE으로 영문 ↔ 한글 변환.
- N+1 회피: select_related("ldong", "ldong__gu").

설계 원칙:
- bbox가 너무 크면 limit (default 200, max 500) 으로 자동 컷.
- limit + 1 fetch → has_more 단순 페이지네이션.
- N+1 회피: select_related("ldong", "ldong__gu").
- location__isnull=False 필수.
- ordering: -contract_date (최신순).

캐싱:
- 5분 TTL django-redis.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from django.contrib.gis.geos import Polygon
from django.core.cache import cache
from django.db.models import Count, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

# sub-plan 7G-B2 (?? 6A): regions.Adong ?? ?? + null fallback ???.
# Adong.adong_code를 직접 사용하여 adong.id → adong.code 매핑 우회.
from apps.public_data.rent_deal.models import (
    DEAL_TYPE_TO_HOUSING_TYPE,
    RentDeal,
)

from .serializers import RentDealPinSerializer

# ---- 상수 ----
DEFAULT_LIMIT = 200
MAX_LIMIT = 500

# total 정확 카운트 상한.
TOTAL_COUNT_CAP_MULTIPLIER = 5

# deal_type 화이트리스트 (응답/요청 영문 enum 5종 + "all"). lock 1.
ALLOWED_DEAL_TYPES = {
    "apt",
    "officetel",
    "yeonlip",
    "dasedae",
    "yeonlip_dasedae",
    "villa",
    "dagagu",
    "danok",
    "all",
}

# 캐시 TTL (SPEC 14.3: API 응답 5분 캐싱).
CACHE_TTL_SECONDS = 300


def _parse_bbox(raw: Optional[str]) -> tuple[float, float, float, float]:
    """
    `bbox=lng1,lat1,lng2,lat2` 파싱.
    """
    if not raw:
        raise ValidationError({"bbox": "bbox 파라미터는 필수입니다 (lng1,lat1,lng2,lat2)."})

    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 4:
        raise ValidationError(
            {"bbox": "bbox는 lng1,lat1,lng2,lat2 4개 값이어야 합니다."}
        )

    try:
        lng1, lat1, lng2, lat2 = (float(p) for p in parts)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"bbox": "bbox 좌표는 숫자여야 합니다."}) from exc

    if lng1 >= lng2 or lat1 >= lat2:
        raise ValidationError(
            {"bbox": "SW(lng1,lat1)가 NE(lng2,lat2)보다 작아야 합니다."}
        )

    if not (124.0 <= lng1 <= 132.0 and 124.0 <= lng2 <= 132.0):
        raise ValidationError({"bbox": "경도(lng)는 124~132 범위여야 합니다 (서울 권역)."})
    if not (33.0 <= lat1 <= 39.0 and 33.0 <= lat2 <= 39.0):
        raise ValidationError({"bbox": "위도(lat)는 33~39 범위여야 합니다 (서울 권역)."})

    return lng1, lat1, lng2, lat2


def _parse_date(raw: Optional[str], key: str) -> Optional[date]:
    """`YYYY-MM-DD` 파싱."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError(
            {key: f"{key} 파라미터는 YYYY-MM-DD 형식이어야 합니다."}
        ) from exc


def _parse_limit(raw: Optional[str]) -> int:
    """`limit` 파싱."""
    if raw is None:
        return DEFAULT_LIMIT
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"limit": "limit는 정수여야 합니다."}) from exc
    if value <= 0:
        raise ValidationError({"limit": "limit는 1 이상이어야 합니다."})
    return min(value, MAX_LIMIT)


def _parse_deal_type(raw: Optional[str]) -> str:
    """`deal_type` 파싱. 응답 lock 1 — 영문 enum 그대로."""
    if raw is None or raw == "":
        return "all"
    if raw not in ALLOWED_DEAL_TYPES:
        allowed = ", ".join(sorted(ALLOWED_DEAL_TYPES))
        raise ValidationError(
            {"deal_type": f"deal_type은 다음 중 하나여야 합니다: {allowed}."}
        )
    return raw


@extend_schema(
    tags=["transactions"],
    summary="bbox 내 전월세 실거래 핀 (메인 지도용)",
    description=(
        "메인 지도(SPEC 6.1) bbox 내 실거래 핀 조회. "
        "sub-plan 4.5B: ldong FK 단일, housing_type 한글 raw, contract_date로 컬럼명 정합. "
        "응답 dict key는 보존 (deal_type/date/dong_name/gu — serializer source 매핑)."
    ),
    parameters=[
        OpenApiParameter(
            name="bbox",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description=(
                "lng1,lat1,lng2,lat2 (SW + NE 코너, WGS84). "
                "예: `126.95,37.55,127.00,37.58`."
            ),
        ),
        OpenApiParameter(
            name="deal_type",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="apt | officetel | villa | dagagu | danok | all (기본: all)",
        ),
        OpenApiParameter(
            name="from",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=False,
            description="YYYY-MM-DD. 지정 시 contract_date >= from.",
        ),
        OpenApiParameter(
            name="to",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=False,
            description="YYYY-MM-DD. 지정 시 contract_date <= to.",
        ),
        OpenApiParameter(
            name="limit",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description=f"기본 {DEFAULT_LIMIT}, 최대 {MAX_LIMIT}.",
        ),
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/RentDealPin"},
                },
                "has_more": {"type": "boolean"},
                "total": {"type": "integer"},
                "has_more_total": {"type": "boolean"},
            },
        }
    },
)
class TransactionsBboxView(APIView):
    """
    GET /api/transactions/bbox

    bbox 내 RentDeal 핀 조회. sub-plan 4.5B 정합:
    - select_related("ldong", "ldong__gu")로 N+1 회피.
    - contract_date/housing_type 컬럼명 정합.
    - 응답 dict key는 RentDealPinSerializer가 source 매핑으로 보존.
    """

    pagination_class = None

    def get(self, request: Request) -> Response:
        # ---- 파라미터 파싱 ----
        lng1, lat1, lng2, lat2 = _parse_bbox(request.query_params.get("bbox"))
        deal_type = _parse_deal_type(request.query_params.get("deal_type"))
        date_from = _parse_date(request.query_params.get("from"), "from")
        date_to = _parse_date(request.query_params.get("to"), "to")
        limit = _parse_limit(request.query_params.get("limit"))

        # ---- 캐시 키 ----
        cache_key = (
            "tx_bbox:"
            f"{lng1:.6f},{lat1:.6f},{lng2:.6f},{lat2:.6f}|"
            f"dt={deal_type}|from={date_from}|to={date_to}|lim={limit}"
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        # ---- 쿼리 ----
        bbox_poly = Polygon.from_bbox((lng1, lat1, lng2, lat2))
        bbox_poly.srid = 4326

        qs = (
            RentDeal.objects.select_related("ldong", "ldong__gu")
            .filter(location__isnull=False, location__within=bbox_poly)
        )
        if deal_type != "all":
            # 응답 영문 enum (lock 1) → 한글 raw로 변환해서 DB 필터.
            if deal_type == "villa":
                qs = qs.filter(housing_type__in=["연립", "다세대", "연립다세대"])
            else:
                housing_type_kr = DEAL_TYPE_TO_HOUSING_TYPE.get(deal_type)
                if housing_type_kr is not None:
                    qs = qs.filter(housing_type=housing_type_kr)
        if date_from is not None:
            qs = qs.filter(contract_date__gte=date_from)
        if date_to is not None:
            qs = qs.filter(contract_date__lte=date_to)

        qs = qs.order_by("-contract_date", "-id")

        # ---- has_more 판정용 limit + 1 fetch ----
        rows = list(qs[: limit + 1])
        has_more = len(rows) > limit
        items = rows[:limit]

        # ---- total 카운트 (cap 적용) ----
        total_cap = limit * TOTAL_COUNT_CAP_MULTIPLIER
        total = qs[: total_cap + 1].count()
        has_more_total = total > total_cap
        if has_more_total:
            total = total_cap

        payload = {
            "items": RentDealPinSerializer(items, many=True).data,
            "has_more": has_more,
            "total": total,
            "has_more_total": has_more_total,
        }

        cache.set(cache_key, payload, timeout=CACHE_TTL_SECONDS)
        return Response(payload, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 대시보드 §4.5 — 파생 지표 (자취촌 지수 + 계약 활발도)
# ---------------------------------------------------------------------------

# 자취촌 지수 가중치 (SPEC §4.5)
STUDIO_W_NON_APT = 0.5
STUDIO_W_SMALL = 0.3
STUDIO_W_MONTHLY_NORM = 0.2

# 소형 면적 임계값 (m²) — SPEC §4.5
SMALL_AREA_M2 = 25.0

# 최근 12개월 윈도우 (SPEC §4.5)
WINDOW_DAYS = 365

# 426동 통째 dict 캐시 TTL (5시간).
DERIVED_CACHE_TTL_SECONDS = 5 * 60 * 60

# 캐시 키 버전 (응답 모양 변경 시 bump)
