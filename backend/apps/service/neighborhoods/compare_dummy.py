"""
동네 비교(SPEC 6.4) 응답용 더미 빌더.

7개 비교 지표(SPEC 6.4)를 한 행으로 빌드한다. 기존 더미 룰을 재사용하여
AdongSummarySerializer / detail_dummy와 일관성 유지:

- score: composite_score 가중합 (소수 둘째자리)
- rent_avg: 120 - score_rent 룰 (AdongSummarySerializer.get_rent_avg와 동일, 더미 raw)
- rent_converted_avg: RentDeal 환산월세(보증금 0.005/월 환산) 평균. <3건 fallback 적용
- transit_min: NEAREST_STATIONS_FALLBACK 1위 walking_min (없으면 폴백 10)
- amenity_label: 충분/보통/부족 (한국어, SPEC 6.4 명시)

10단계 실데이터 적재 후에도 응답 키 형태는 변하지 않도록 빌더만 교체하면 됨.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from apps.public_data.rent_deal.models import RentDeal
from apps.public_data.rent_deal.utils import convert_to_monthly

from .adong_surface import composite_score as _composite_score
from .detail_dummy import NEAREST_STATIONS_FALLBACK


# 폴백 통학 시간 (NEAREST_STATIONS_FALLBACK에 없는 slug용 — 10단계 실 데이터 시 교체)
TRANSIT_MIN_FALLBACK = 10

# 환산월세 평균 산출 시 거래량 임계치 (SPEC 14.2: <3건 동은 단독 평균 미신뢰).
# service scoring updater 의 rent metric 계산과 동일한 임계.
RENT_MIN_DEALS_FOR_DIRECT_AVG = 3


def compute_rent_converted_avgs(adongs: Iterable) -> Dict[str, Optional[int]]:
    """???? ????(??, ??) ?? ?? ??.

    rent_deal.adong_code? ?? ????? ??? ??? ????.
    ??? 3? ???? ?? ???? None? ????.
    """
    target_adongs = list(adongs)
    if not target_adongs:
        return {}

    result: Dict[str, Optional[int]] = {}
    for adong in target_adongs:
        rows = RentDeal.objects.filter(adong_id=adong.code).values_list(
            "deposit", "monthly_rent"
        )
        vals = [convert_to_monthly(deposit, rent) for deposit, rent in rows]
        result[adong.slug] = (
            round(sum(vals) / len(vals))
            if len(vals) >= RENT_MIN_DEALS_FOR_DIRECT_AVG
            else None
        )
    return result


def _amenity_label_ko(score_amenity: float) -> str:
    """SPEC 6.4 — 비교표에 표기할 한국어 레이블."""
    if score_amenity >= 70:
        return "충분"
    if score_amenity >= 40:
        return "보통"
    return "부족"


def _safety_label_ko(score_transit: float) -> str:
    """SPEC 6.4 안전 지수 — 한국어 레이블.
    실 안전 데이터(범죄율/CCTV)는 추후 적재 예정. 현재는 transit 점수 기반 임시 매핑
    (AdongSummarySerializer.get_safety_level과 동일 임계값, 라벨만 한국어).
    """
    if score_transit >= 70:
        return "높음"
    if score_transit >= 40:
        return "보통"
    return "낮음"




def build_compare_row(
    adong,
    weights: dict,
    rent_converted_avg: Optional[int] = None,
) -> dict:
    """
    SPEC 6.4 비교 응답 한 행을 빌드.

    파라미터:
        adong: Adong 인스턴스 (centroid 미사용, score_*만 필요)
        weights: {"rent": 0~1, "amenity": 0~1, "transit": 0~1} 합 1
        rent_converted_avg: 환산월세(만원, 정수) 또는 None.
            view 가 compute_rent_converted_avgs 로 사전 계산해 전달.
            누락(None)이면 응답 필드에 null 노출.

    반환: snake_case dict (CompareResponse.adongs[i] 그대로).
    """
    # 7G-B1: Adong.composite_score 메서드 제거 → adong_surface.composite_score 함수.
    score = round(
        _composite_score(
            adong,
            w_rent=weights["rent"],
            w_amenity=weights["amenity"],
            w_transit=weights["transit"],
        ),
        2,
    )

    # 평균 월세 (raw 더미) — AdongSummarySerializer.get_rent_avg와 동일 룰 (120 - score_rent)
    # 주의: 이 값은 score_rent 로 역산한 더미라 실 raw 평균 아님. frontend 가
    # 점진적으로 rent_converted_avg 로 전환해야 함 (misleading 케이스 해결).
    rent_avg = max(0, int(120 - adong.score_rent))

    # 통학 시간 — NEAREST_STATIONS_FALLBACK 1위의 walking_min
    stations = NEAREST_STATIONS_FALLBACK.get(adong.slug)
    if stations:
        transit_min = int(stations[0]["walking_min"])
    else:
        transit_min = TRANSIT_MIN_FALLBACK

    return {
        "slug": adong.slug,
        "name": adong.name,
        "gu": adong.gu,
        "score": score,
        "rent_avg": rent_avg,
        "rent_converted_avg": rent_converted_avg,
        "transit_min": transit_min,
        "amenity_label": _amenity_label_ko(adong.score_amenity),
        "safety_label": _safety_label_ko(adong.score_transit),
    }
