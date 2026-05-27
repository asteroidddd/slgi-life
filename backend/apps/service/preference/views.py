"""
선호 학습 (SPEC 6.5, 11.4) 관련 뷰.

엔드포인트:
- GET /api/preference/pairs?count=5
  → 비교용 동네 쌍 N개 반환 (정보량 최대화 휴리스틱)
- POST /api/preference/submit
  body: {"comparisons": [{"won": slug_a, "lost": slug_b}, ...]}
  → {"w_rent": int, "w_amenity": int, "w_transit": int} (합 100)

7단계는 무상태 API. UserPreference 모델 저장은 9단계(인증)에서 추가.
"""

from __future__ import annotations

from itertools import combinations

from django.db.models import F, FloatField, Value
from django.db.models.functions import Coalesce
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.service.neighborhoods.compare_dummy import compute_rent_converted_avgs
from apps.service.neighborhoods.detail_dummy import NEAREST_STATIONS_FALLBACK
# sub-plan 7G-B2: Adong → Adong + CurrentAdong join 치환.
# 결정 1A: current_adong 미존재 또는 score_rent NULL → 0 fallback.
from apps.public_data.regions.models import Adong

from .optimizer import estimate_weights, to_integer_percent


# 기본 가중치 (SPEC 6.1 — 첫 진입 시 33/33/34)
DEFAULT_WEIGHTS = {"rent": 33 / 100, "amenity": 33 / 100, "transit": 34 / 100}

# 한국어 라벨 매핑 (AdongSummarySerializer.amenity_level과 일관)
AMENITY_LABEL_KO: dict[str, str] = {
    "sufficient": "충분",
    "normal": "보통",
    "lacking": "부족",
}


# ---------------------------------------------------------------------------
# 카드 변환 — 동 1개 → 비교 카드 dict
# ---------------------------------------------------------------------------


def _amenity_level(score_amenity: float) -> str:
    """AdongSummarySerializer.get_amenity_level과 동일 임계값."""
    if score_amenity >= 70:
        return "sufficient"
    if score_amenity >= 40:
        return "normal"
    return "lacking"


def _transit_min(slug: str) -> int:
    """가장 가까운 역의 도보 분 (NEAREST_STATIONS_FALLBACK 1위). 없으면 더미 10분."""
    stations = NEAREST_STATIONS_FALLBACK.get(slug)
    if stations:
        return int(stations[0]["walking_min"])
    return 10


def _build_card(
    adong: Adong,
    weights: dict[str, float],
    rent_converted: int | None = None,
) -> dict:
    """
    SPEC 6.5 모달의 동 카드 한 장.

    필드:
      - rent_avg: 더미 (120 - score_rent). 호환성 위해 보존.
      - rent_converted: 환산월세(만원, 정수) 평균 또는 None.
        view 가 compute_rent_converted_avgs 로 사전 계산해 전달.
        보증금이 큰 동(반전세 다수)이 raw 월세만 보면 부당하게 싸 보이는
        문제를 해결. 5번 비교에서 사용자가 보는 "월세" 표기는 이 값 사용.
      - amenity_label: 한국어.
      - transit_min: NEAREST_STATIONS_FALLBACK 1위.

    sub-plan 7G-B2: Adong + CurrentAdong annotate 합성. score_* 속성은
    queryset annotate(`score_rent`/`score_amenity`/`score_transit`)로 노출.
    응답 dict key는 보존 (slug/name/gu/rent_avg/rent_converted/transit_min/
    amenity_label/score).
    """
    rent_avg = max(0, int(120 - adong.score_rent))
    transit_min = _transit_min(adong.slug)
    level = _amenity_level(adong.score_amenity)
    composite = (
        adong.score_rent * weights["rent"]
        + adong.score_amenity * weights["amenity"]
        + adong.score_transit * weights["transit"]
    )
    return {
        "slug": adong.slug,
        "name": adong.name,
        "gu": adong.gu.name,
        "rent_avg": rent_avg,
        "rent_converted": rent_converted,
        "transit_min": transit_min,
        "amenity_label": AMENITY_LABEL_KO[level],
        "score": round(composite, 2),
    }


# ---------------------------------------------------------------------------
# 쌍 선택 알고리즘
# ---------------------------------------------------------------------------


def _select_pairs(adongs: list[Adong], count: int) -> list[tuple[Adong, Adong]]:
    """
    정보량 최대화 휴리스틱.

    축(rent / amenity / transit) 별로 점수 차가 가장 큰 동 쌍을 우선 선택.
    축 라운드 로빈으로 count 개를 채운다 — 같은 축이라도 차순위 쌍을 골라
    한쪽 축에 편중되지 않게.

    동 5개 (n=5)면 가능한 쌍은 10. 같은 쌍 중복은 회피하지만, count > 10이면
    축별 우선순위에 따라 결국 다 소진하고 부족분은 라운드 로빈으로 반복 허용.
    더미 환경에서도 항상 count 개 반환을 보장.
    """
    if len(adongs) < 2:
        return []

    # 모든 가능한 (i, j) 쌍 (i < j)
    pairs = list(combinations(range(len(adongs)), 2))

    # 축별로 (|차이|, i, j) 내림차순 정렬한 인덱스 리스트 생성
    axes = [
        ("score_rent", lambda d: d.score_rent),
        ("score_amenity", lambda d: d.score_amenity),
        ("score_transit", lambda d: d.score_transit),
    ]
    axis_pairs: list[list[tuple[int, int]]] = []
    for _, getter in axes:
        ranked = sorted(
            pairs,
            key=lambda ij, g=getter: abs(g(adongs[ij[0]]) - g(adongs[ij[1]])),
            reverse=True,
        )
        axis_pairs.append(ranked)

    # 라운드 로빈으로 축을 돌면서 다음 쌍 뽑기. 중복은 일단 회피.
    seen: set[tuple[int, int]] = set()
    selected: list[tuple[int, int]] = []
    cursors = [0, 0, 0]
    axis_idx = 0
    # 충분한 시도 횟수 (모든 쌍을 한 바퀴 다 돌고도 안 차면 중복 허용으로 fallback)
    max_attempts = len(pairs) * len(axes) + count
    attempts = 0
    while len(selected) < count and attempts < max_attempts:
        ranked = axis_pairs[axis_idx]
        while cursors[axis_idx] < len(ranked) and ranked[cursors[axis_idx]] in seen:
            cursors[axis_idx] += 1
        if cursors[axis_idx] < len(ranked):
            ij = ranked[cursors[axis_idx]]
            cursors[axis_idx] += 1
            seen.add(ij)
            selected.append(ij)
        axis_idx = (axis_idx + 1) % len(axes)
        attempts += 1

    # 부족분은 첫 축 기준 가장 차이 큰 쌍부터 다시 (중복 허용 — 더미 환경 보호)
    while len(selected) < count:
        ij = axis_pairs[0][len(selected) % len(axis_pairs[0])]
        selected.append(ij)

    return [(adongs[i], adongs[j]) for i, j in selected]


# ---------------------------------------------------------------------------
# 뷰
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["preference"],
    summary="선호 학습용 동네 쌍 (SPEC 6.5)",
    description="정보량 최대화 휴리스틱으로 양극단 쌍 우선 N개 반환.",
    parameters=[
        OpenApiParameter(
            name="count",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="반환할 쌍 개수 (1~20, default 5).",
        ),
    ],
)
class PreferencePairsView(APIView):
    """
    GET /api/preference/pairs?count=5

    SPEC 6.5 — 5번 비교용 쌍을 반환. 응답:
      {"pairs": [{"left": <card>, "right": <card>}, ...]}
    """

    pagination_class = None

    def get(self, request: Request) -> Response:
        # count 파라미터 (기본 5, 1~20 범위)
        raw = request.query_params.get("count", "5")
        try:
            count = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"count": "정수여야 합니다."}) from exc
        if not 1 <= count <= 20:
            raise ValidationError({"count": "1~20 범위여야 합니다."})

        # sub-plan 7G-B2: Adong + CurrentAdong join + annotate score_*.
        # 결정 1A: current_adong 미존재/score NULL → 0.
        adongs = list(
            Adong.objects.select_related("gu").annotate(
                score_rent=Coalesce(
                    F("current_score__score_rent"),
                    Value(0.0),
                    output_field=FloatField(),
                ),
                score_amenity=Coalesce(
                    F("current_score__score_amenity"),
                    Value(0.0),
                    output_field=FloatField(),
                ),
                score_transit=Coalesce(
                    F("current_score__score_transit"),
                    Value(0.0),
                    output_field=FloatField(),
                ),
            )
        )
        if len(adongs) < 2:
            raise ValidationError(
                {"detail": "비교할 동이 부족합니다 (최소 2개 필요)."}
            )

        pair_dongs = _select_pairs(adongs, count)

        # 환산월세 평균을 한 번에 사전 계산 (N+1 회피).
        # 같은 구의 RentDeal 만 fetch 하므로 비용 제한적. compute_rent_converted_avgs
        # 가 같은 fallback 정책 (≥3건 직접 / 같은 구 / 서울 중위) 적용.
        unique_dongs = list({d.slug: d for pair in pair_dongs for d in pair}.values())
        rent_converted_map = compute_rent_converted_avgs(unique_dongs)

        pairs = [
            {
                "left": _build_card(
                    left,
                    DEFAULT_WEIGHTS,
                    rent_converted=rent_converted_map.get(left.slug),
                ),
                "right": _build_card(
                    right,
                    DEFAULT_WEIGHTS,
                    rent_converted=rent_converted_map.get(right.slug),
                ),
            }
            for left, right in pair_dongs
        ]
        return Response({"pairs": pairs}, status=status.HTTP_200_OK)


@extend_schema(
    tags=["preference"],
    summary="비교 결과 → 가중치 추정 (SPEC 11.4)",
    description=(
        "사용자가 N번 비교한 결과 (won/lost 슬러그 쌍 배열)를 받아 "
        "scipy.optimize SLSQP로 가중치를 추정. 결과는 합 100 정수 %."
    ),
)
class PreferenceSubmitView(APIView):
    """
    POST /api/preference/submit
    body: {"comparisons": [{"won": "slug_a", "lost": "slug_b"}, ...]}

    won/lost 슬러그 → Adong → (score_rent, score_amenity, score_transit) 추출
    → estimate_weights → 정수 % 변환 → 응답.

    응답: {"w_rent": int, "w_amenity": int, "w_transit": int}  (합 100)

    오류:
      - body 형식 불일치 → 400
      - comparisons 빈 배열 → 400
      - won == lost (같은 슬러그) → 400
      - slug 미존재 → 400 (어느 슬러그인지 명시)
    """

    def post(self, request: Request) -> Response:
        data = request.data
        if not isinstance(data, dict):
            raise ValidationError({"detail": "JSON 객체여야 합니다."})

        comparisons_raw = data.get("comparisons")
        if not isinstance(comparisons_raw, list):
            raise ValidationError(
                {"comparisons": "리스트여야 합니다."}
            )
        if len(comparisons_raw) == 0:
            raise ValidationError(
                {"comparisons": "최소 1개 이상의 비교가 필요합니다."}
            )
        # 잠금장치: 너무 많은 비교는 거부 (남용 방지 / 응답 시간 보호)
        if len(comparisons_raw) > 50:
            raise ValidationError(
                {"comparisons": "비교는 최대 50개까지만 처리할 수 있습니다."}
            )

        # 슬러그 수집 + 형식 검증
        slugs_needed: set[str] = set()
        validated: list[tuple[str, str]] = []
        for i, c in enumerate(comparisons_raw):
            if not isinstance(c, dict):
                raise ValidationError(
                    {"comparisons": f"{i}번 항목이 객체가 아닙니다."}
                )
            won = c.get("won")
            lost = c.get("lost")
            if not isinstance(won, str) or not isinstance(lost, str):
                raise ValidationError(
                    {
                        "comparisons": (
                            f"{i}번 항목의 won/lost는 문자열 슬러그여야 합니다."
                        )
                    }
                )
            if won == lost:
                raise ValidationError(
                    {
                        "comparisons": (
                            f"{i}번 항목의 won과 lost가 같은 슬러그입니다 ('{won}')."
                        )
                    }
                )
            validated.append((won, lost))
            slugs_needed.add(won)
            slugs_needed.add(lost)

        # 슬러그 → Adong 일괄 조회 (N+1 방지). sub-plan 7G-B2.
        # CurrentAdong join + Coalesce annotate. 결정 1A: NULL → 0.
        dong_map: dict[str, Adong] = {
            d.slug: d
            for d in Adong.objects.annotate(
                score_rent=Coalesce(
                    F("current_score__score_rent"),
                    Value(0.0),
                    output_field=FloatField(),
                ),
                score_amenity=Coalesce(
                    F("current_score__score_amenity"),
                    Value(0.0),
                    output_field=FloatField(),
                ),
                score_transit=Coalesce(
                    F("current_score__score_transit"),
                    Value(0.0),
                    output_field=FloatField(),
                ),
            ).filter(slug__in=slugs_needed)
        }
        missing = sorted(slugs_needed - set(dong_map.keys()))
        if missing:
            raise ValidationError(
                {
                    "comparisons": (
                        f"존재하지 않는 동 슬러그: {', '.join(missing)}"
                    )
                }
            )

        # (won_features, lost_features) 튜플 리스트.
        # rent feature 는 adong.score_rent 사용 — score_rent 는 service scoring updater 가
        # 환산월세(보증금×0.005 + 월세, apps.public_data.rent_deal.utils.convert_to_monthly)
        # 분포의 백분위로 산출하므로 이미 환산 기반이다. 따라서 학습 로직은
        # raw 월세가 아닌 환산월세 차이를 비교한다 (rent metric 환산 통일).
        comparisons: list[
            tuple[tuple[float, float, float], tuple[float, float, float]]
        ] = []
        for won_slug, lost_slug in validated:
            won = dong_map[won_slug]
            lost = dong_map[lost_slug]
            comparisons.append(
                (
                    (won.score_rent, won.score_amenity, won.score_transit),
                    (lost.score_rent, lost.score_amenity, lost.score_transit),
                )
            )

        weights = estimate_weights(comparisons)
        percent = to_integer_percent(weights)
        return Response(
            {
                "w_rent": percent["rent"],
                "w_amenity": percent["amenity"],
                "w_transit": percent["transit"],
            },
            status=status.HTTP_200_OK,
        )
