"""Phase 5 — 메인 지도 자취 거래량 분포 (Studio Match).

`/adong/:slug/explore`(Phase 4.8)와 동일한 base filter 를 받아 한 번에 모든 동에
대해 GROUP BY count + ratio 정규화. 메인 지도 히트맵의 'match 모드' 가 이 응답으로
색칠된다.

데이터 = 국토부 실거래 (rent_deal) 최근 N개월. 현재 매물 재고가 아닌 과거 거래량
분포 (eng-review #18, codex outside voice).

엔드포인트
----------
- GET /api/adongs/match-counts?<filters>     (AdongMatchCountsView)
    응답: { filters_applied, total_matched, min_sample, adongs[] }
- GET /api/adongs/<slug>/match-detail?<filters>  (AdongMatchDetailView)
    응답: { adong, filters_applied, count, avg_converted_rent, avg_deposit,
            match_ratio, period_total }

성능 / 캐시
----------
- SQL groups filtered rent_deal rows by adong_id.
- Redis 5 minute TTL. Cache key = sha1(canonicalized filters).

RentDeal scope
--------------
- Uses only rent_deal rows with confirmed adong_code.
- Response keys are preserved for the frontend contract.

Ratio normalization (eng-review #3)
-----------------------------------
log scale + min_sample (default 10):
    ratio = log1p(count) / log1p(max_count) * 100
    count < min_sample → ratio = 0
극단 outlier 동(예: 5,000건 vs 50건)이 100 vs 1 로 과장되지 않게.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from typing import Any

from django.core.cache import cache
from django.db.models import Avg, Count, F, Value
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public_data.rent_deal.models import (
    DEAL_TYPE_TO_HOUSING_TYPE,
    RentDeal,
)

from .adong_surface import build_adong_qs, wrap
from .explore import (
    PERIOD_TO_DAYS,
    apply_base_filters,
    parse_base_filters,
)


# 표본 부족 동 임계 (eng-review #3)
MIN_SAMPLE = 10

# Redis cache TTL (sec)
CACHE_TTL = 300

# 환산월세 SQL expression (apps.public_data.rent_deal.utils 와 동일 계수 0.005)
CONVERTED_EXPR = F("monthly_rent") + F("deposit") * Value(0.005)


def canonicalize_filters(filters: dict[str, Any]) -> str:
    """필터 dict → 정렬·default omit 한 sha1 캐시 키 (eng-review #10)."""
    canonical: dict[str, Any] = {}
    for k in sorted(filters):
        v = filters[k]
        if isinstance(v, (list, tuple)):
            v = ",".join(sorted(map(str, v)))
        canonical[k] = v
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _normalize_ratio(count: int, max_count: int) -> float:
    """log scale 정규화 0~100. count<MIN_SAMPLE 또는 max==0 → 0."""
    if count < MIN_SAMPLE or max_count <= 0:
        return 0.0
    return round(math.log1p(count) / math.log1p(max_count) * 100, 1)


# ---------------------------------------------------------------------------
# match-counts (전체 동 카운트)
# ---------------------------------------------------------------------------


def compute_match_counts(filters: dict[str, Any], today: date) -> dict[str, Any]:
    """Count filtered rent deals per adong using confirmed adong_code rows."""
    cache_key = f"match-counts:{canonicalize_filters(filters)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = apply_base_filters(RentDeal.objects.filter(adong_id__isnull=False), filters, today)
    rows = qs.values("adong_id").annotate(cnt=Count("id"))
    counts_by_adong_code: dict[str, int] = {
        r["adong_id"]: r["cnt"]
        for r in rows
        if r["adong_id"] is not None
    }

    from apps.public_data.regions.models import Adong  # noqa: WPS433

    all_adongs = list(
        Adong.objects.select_related("gu").values("adong_code", "slug")
    )
    max_count = max(counts_by_adong_code.values()) if counts_by_adong_code else 0
    total_matched = sum(counts_by_adong_code.values())

    adong_items: list[dict[str, Any]] = []
    for item in all_adongs:
        cnt = counts_by_adong_code.get(item["adong_code"], 0)
        adong_items.append(
            {
                "code": item["adong_code"],
                "slug": item["slug"],
                "count": cnt,
                "ratio": _normalize_ratio(cnt, max_count),
                "has_data": True,
            }
        )

    response = {
        "filters_applied": filters,
        "total_matched": total_matched,
        "min_sample": MIN_SAMPLE,
        "adongs": adong_items,
    }
    cache.set(cache_key, response, CACHE_TTL)
    return response


class AdongMatchCountsView(APIView):
    """GET /api/adongs/match-counts?<filters>"""

    def get(self, request: Request) -> Response:
        filters = parse_base_filters(request)
        data = compute_match_counts(filters, today=date.today())
        return Response(data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# match-detail (동 패널 KPI 카드)
# ---------------------------------------------------------------------------


def compute_match_detail(adong, filters: dict[str, Any], today: date) -> dict[str, Any]:
    """Return match stats for one adong and its period/type denominator."""
    cache_key = (
        f"match-detail:{adong.id}:{canonicalize_filters(filters)}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 1) 필터 통과 거래 (이 동 + base filter)
    matched_qs = apply_base_filters(
        RentDeal.objects.filter(adong_id=adong.code), filters, today
    )
    matched_agg = matched_qs.aggregate(
        n=Count("id"),
        avg_rent=Avg(CONVERTED_EXPR),
        avg_deposit=Avg("deposit"),
    )

    # 2) Denominator: same adong/period/deal_types set (ignores deposit/monthly/area).
    # 응답 영문 enum → DB 한글 housing_type 변환 (lock 1).
    housing_types = [
        DEAL_TYPE_TO_HOUSING_TYPE[k]
        for k in filters["deal_types"]
        if k in DEAL_TYPE_TO_HOUSING_TYPE
    ]
    period_qs = RentDeal.objects.filter(
        adong_id=adong.code, housing_type__in=housing_types
    )
    days = PERIOD_TO_DAYS[filters["period"]]
    if days is not None:
        from datetime import timedelta
        period_qs = period_qs.filter(contract_date__gte=today - timedelta(days=days))
    period_total = period_qs.count()

    count = int(matched_agg["n"] or 0)
    match_ratio = round(count / period_total * 100, 1) if period_total > 0 else None

    response = {
        "adong": {
            "slug": adong.slug,
            "code": adong.code,
            "name": adong.name,
            "gu": adong.gu,
        },
        "filters_applied": filters,
        "count": count,
        "avg_converted_rent": int(round(float(matched_agg["avg_rent"])))
        if matched_agg["avg_rent"] is not None
        else None,
        "avg_deposit": int(round(float(matched_agg["avg_deposit"])))
        if matched_agg["avg_deposit"] is not None
        else None,
        "match_ratio": match_ratio,
        "period_total": period_total,
    }
    cache.set(cache_key, response, CACHE_TTL)
    return response


class AdongMatchDetailView(APIView):
    """GET /api/adongs/<slug>/match-detail?<filters>"""

    def get(self, request: Request, slug: str) -> Response:
        # 7G-B1: Adong + current_score 합성. compute_match_detail은 slug/code/name/gu/id만 사용.
        from apps.public_data.regions.models import Adong  # noqa: WPS433

        try:
            adong = build_adong_qs().get(slug=slug)
        except Adong.DoesNotExist as exc:
            raise NotFound({"detail": "동을 찾을 수 없습니다."}) from exc
        adong = wrap(adong)
        filters = parse_base_filters(request)
        data = compute_match_detail(adong, filters, today=date.today())
        return Response(data, status=status.HTTP_200_OK)
