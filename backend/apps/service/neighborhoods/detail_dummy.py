"""
동네 상세 페이지(SPEC 6.3) 응답용 더미 빌더.

10단계 data-pipeline이 실 데이터(전월세 거래 / 편의시설 카운트 / 지하철 위치 /
리뷰)를 적재하기 전까지 사용하는 점수 기반 합리적 더미 생성기.

핵심 원칙:
- 같은 slug + 같은 가중치 → 같은 응답 (deterministic). slug 해시를 시드로 사용.
- 점수와 모순되지 않게: score_rent 높은 동은 평균 월세 낮게, score_amenity
  높은 동은 편의시설 카운트 많게, etc.
- "거래 3건 미만 월" SPEC 14.2 — villa/dagagu/danok/officetel 별로 가끔 None이 나오게
  하여 프론트가 점선 처리 케이스를 다룰 수 있게 함.

이 모듈은 마이그레이션이나 DB 변경을 포함하지 않는다. 데이터 적재 후 본
모듈은 제거 또는 실 쿼리 기반 빌더로 교체될 예정이다.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from typing import Iterable

from .adong_surface import build_adong_qs, composite_score as _composite_score, wrap
from .summary import generate_summary


# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

SEOUL_AVG_BASELINE = 65  # 서울 평균 가정치 (vs_seoul_avg_pct 계산용)

# SPEC 6.3 섹션 3 — 8개 카테고리. 각 카테고리의 "이상적인 동에서의 카운트" 가중.
AMENITY_CATEGORIES: list[tuple[str, float]] = [
    ("편의점", 0.95),       # 어디든 많음
    ("카페", 1.10),         # 점수 높을수록 많음
    ("음식점", 1.40),       # 가장 많음
    ("마트", 0.30),         # 적은 편
    ("병원·약국", 0.55),
    ("스터디카페", 0.25),
    ("세탁소", 0.20),
    ("올리브영", 0.15),
]

# SPEC 6.3 섹션 2 — 보증금 대역 5개.
# 보증금 클수록 월세 낮게 가는 것이 일반적 (전월세 전환).
DEPOSIT_BANDS: list[tuple[str, float]] = [
    ("0", 1.00),       # 보증금 0 → 월세 가장 비쌈 (월세 100%)
    ("500", 0.85),     # 보증금 500 → 월세 85%
    ("1000", 0.70),
    ("2000", 0.55),
    ("3000+", 0.40),   # 보증금 3000 이상 → 월세 40%
]

# SPEC 6.3 섹션 2 하단 표 유형 3종 (DB 스키마와 동일 선택지)
DEAL_TYPES = ["연립다세대", "단독다가구", "오피스텔"]

# SPEC 6.3 섹션 4 — 가까운 역 매핑 (slug별 1~3위).
# 1위는 AdongSummarySerializer의 NEAREST_STATION_FALLBACK과 일관.
NEAREST_STATIONS_FALLBACK: dict[str, list[dict]] = {
    "pildong": [
        {"name": "충무로", "line": "4호선", "walking_min": 8, "walking_distance_m": 560},
        {"name": "명동", "line": "4호선", "walking_min": 12, "walking_distance_m": 840},
        {"name": "동대입구", "line": "3호선", "walking_min": 14, "walking_distance_m": 980},
    ],
    "hoegidong": [
        {"name": "회기", "line": "1호선", "walking_min": 5, "walking_distance_m": 350},
        {"name": "외대앞", "line": "1호선", "walking_min": 9, "walking_distance_m": 630},
        {"name": "경희대", "line": "경의중앙", "walking_min": 11, "walking_distance_m": 770},
    ],
    "seogyodong": [
        {"name": "홍대입구", "line": "2호선", "walking_min": 7, "walking_distance_m": 490},
        {"name": "합정", "line": "2/6호선", "walking_min": 10, "walking_distance_m": 700},
        {"name": "상수", "line": "6호선", "walking_min": 12, "walking_distance_m": 840},
    ],
    "yeoksamdong": [
        {"name": "역삼", "line": "2호선", "walking_min": 4, "walking_distance_m": 280},
        {"name": "선릉", "line": "2/수인분당", "walking_min": 8, "walking_distance_m": 560},
        {"name": "강남", "line": "2호선", "walking_min": 13, "walking_distance_m": 910},
    ],
    "jamsildong": [
        {"name": "잠실", "line": "2/8호선", "walking_min": 6, "walking_distance_m": 420},
        {"name": "잠실나루", "line": "2호선", "walking_min": 10, "walking_distance_m": 700},
        {"name": "잠실새내", "line": "2호선", "walking_min": 12, "walking_distance_m": 840},
    ],
}

# 기본 폴백 (5개 더미 외 slug — 10단계에서 본 데이터로 교체)
NEAREST_STATIONS_DEFAULT: list[dict] = [
    {"name": "정보 없음", "line": "-", "walking_min": 0, "walking_distance_m": 0},
    {"name": "정보 없음", "line": "-", "walking_min": 0, "walking_distance_m": 0},
    {"name": "정보 없음", "line": "-", "walking_min": 0, "walking_distance_m": 0},
]

# SPEC 6.3 섹션 5 — 자취생 리뷰 더미 본문 풀.
# 상세 페이지 5단계가 화면을 만들 수 있게 텍스트 다양성 확보.
REVIEW_POOL: list[dict] = [
    {
        "title": "교통 진짜 편해요",
        "author_school": "동국대",
        "body": "버스, 지하철 둘 다 가까워서 통학할 때 한 번도 늦은 적 없어요. 다만 밤에 약간 시끄러운 편.",
    },
    {
        "title": "월세 대비 만족",
        "author_school": "한국외대",
        "body": "이 가격에 이 정도 인프라면 가성비 최고. 대형 마트는 좀 멀지만 편의점은 5분 안에 다 있어요.",
    },
    {
        "title": "조용해서 좋아요",
        "author_school": "홍익대",
        "body": "골목 안쪽이라 한적하고 공부하기 좋습니다. 카페도 다양한 편이라 자취생 많은 듯.",
    },
    {
        "title": "생활 인프라 굿",
        "author_school": "경희대",
        "body": "병원, 약국, 마트가 도보권 안에 다 있어서 자취 처음이라도 적응 쉬웠어요.",
    },
    {
        "title": "강추 동네",
        "author_school": "서울대",
        "body": "일주일 살아보고 바로 1년 계약했어요. 회사·학교 모두 30분 안.",
    },
    {
        "title": "월세는 좀 비싸요",
        "author_school": "연세대",
        "body": "교통이랑 시설 다 좋은데 월세가 만만치 않습니다. 보증금 올리면 월세 부담은 줄어드는 편.",
    },
    {
        "title": "야경 예쁘네요",
        "author_school": "고려대",
        "body": "한강 가까운 동네라 산책하기 좋아요. 다만 주말엔 사람이 많아서 좀 붐벼요.",
    },
    {
        "title": "혼밥 천국",
        "author_school": "중앙대",
        "body": "1인 식당이 정말 많아서 자취 입문자한테 너무 좋아요. 빨래방, 세탁소도 골목마다 있음.",
    },
]


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------


def _seeded_rng(slug: str, weights: dict | None = None, salt: str = "") -> random.Random:
    """
    slug를 시드로 한 결정적 RNG. 같은 입력 → 같은 출력.
    가중치까지 시드에 포함하면 슬라이더 변경마다 응답 흔들리니, weights는 시드에서 제외.
    """
    seed_str = f"{slug}|{salt}"
    h = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16)
    return random.Random(h)


def _amenity_level(score_amenity: float) -> str:
    """SPEC 6.3 섹션 3 — 상위 33% 충분 / 중간 33% 보통 / 하위 33% 부족.
    현재 5개 더미 기준이라 70/40 임계값 사용 (10단계에서 서울 백분위로 교체)."""
    if score_amenity >= 70:
        return "sufficient"
    if score_amenity >= 40:
        return "normal"
    return "lacking"


def _format_month(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _round1(x: float) -> float:
    return round(x, 1)


# ---------------------------------------------------------------------------
# 섹션 빌더
# ---------------------------------------------------------------------------


def _build_real_estate(adong, today: date) -> dict:
    """SPEC 6.3 섹션 2 — 부동산 시세."""
    rng = _seeded_rng(adong.slug, salt="real_estate")

    # 마지막 달 평균 ~= 120 - score_rent (AdongSummarySerializer.get_rent_avg와 일관)
    base = max(20, 120 - adong.score_rent)

    # ---- 월별 추이 (최근 6개월) ----
    monthly_trend = []
    cur = date(today.year, today.month, 1)
    months: list[date] = []
    for _ in range(6):
        months.append(cur)
        # 한 달 전
        prev_month = cur.month - 1 or 12
        prev_year = cur.year if cur.month != 1 else cur.year - 1
        cur = date(prev_year, prev_month, 1)
    months.reverse()  # 오래된 → 최신

    for i, m in enumerate(months):
        # 마지막 달 가까워질수록 base에 수렴, 이전 달은 ±5 노이즈
        noise_v = rng.uniform(-5, 5) + (5 - i) * rng.uniform(-0.5, 0.5)
        # 유형별 차이: villa < dagagu < danok < officetel (오피스텔이 가장 비쌈)
        # Phase 1 RDS 통합으로 단독다가구(multi) → 다가구(dagagu) + 단독(danok) 분리.
        villa = base + noise_v - 5
        dagagu = base + noise_v
        danok = base + noise_v + 3
        officetel = base + noise_v + 8

        # SPEC 14.2 — 거래 3건 미만 월은 None. 가끔(~10%) None 처리.
        def maybe_null(v: float) -> float | None:
            if rng.random() < 0.10:
                return None
            return max(10.0, _round1(v))

        monthly_trend.append({
            "month": _format_month(m),
            "villa": maybe_null(villa),
            "dagagu": maybe_null(dagagu),
            "danok": maybe_null(danok),
            "officetel": maybe_null(officetel),
        })

    # ---- 보증금 대역별 평균 월세 ----
    deposit_band_avg = []
    for band, ratio in DEPOSIT_BANDS:
        avg = base * ratio + rng.uniform(-3, 3)
        deposit_band_avg.append({
            "band": band,
            "avg_monthly_rent": max(5.0, _round1(avg)),
        })

    # ---- 최근 실거래 5건 ----
    recent_deals = []
    for i in range(5):
        days_ago = rng.randint(5, 180)
        deal_date = today - timedelta(days=days_ago)
        deal_type = DEAL_TYPES[i % 3]
        area_m2 = round(rng.uniform(15, 45), 1)
        # 보증금: 0 / 500 / 1000 / 2000 / 3000 중 하나
        deposit_choices = [0, 500, 1000, 2000, 3000]
        deposit = rng.choice(deposit_choices)
        # 보증금 클수록 월세 낮게
        ratio = {0: 1.00, 500: 0.85, 1000: 0.70, 2000: 0.55, 3000: 0.40}[deposit]
        monthly_rent = int(round(base * ratio + rng.uniform(-5, 5)))
        recent_deals.append({
            "date": deal_date.isoformat(),
            "type": deal_type,
            "area_m2": area_m2,
            "deposit": deposit,
            "monthly_rent": max(10, monthly_rent),
        })
    # 날짜 내림차순 (최신 → 과거)
    recent_deals.sort(key=lambda d: d["date"], reverse=True)

    return {
        "monthly_trend": monthly_trend,
        "deposit_band_avg": deposit_band_avg,
        "recent_deals": recent_deals,
    }


def _build_amenities(adong) -> list[dict]:
    """SPEC 6.3 섹션 3 — 편의시설 8개 카테고리."""
    rng = _seeded_rng(adong.slug, salt="amenities")
    level = _amenity_level(adong.score_amenity)
    area = max(0.1, adong.area_km2 or 0.25)

    out = []
    for category, weight in AMENITY_CATEGORIES:
        # 점수 0 → 카운트 ~ 1, 점수 100 → 카운트 ~ weight*100
        base_count = int(round(adong.score_amenity * weight + rng.uniform(-3, 3)))
        count = max(0, base_count)
        density = round(count / area, 1)
        out.append({
            "category": category,
            "count": count,
            "density_per_km2": density,
            "level": level,
        })
    return out


def _build_transit(adong) -> dict:
    """SPEC 6.3 섹션 4 — 교통."""
    rng = _seeded_rng(adong.slug, salt="transit")

    stations_raw = NEAREST_STATIONS_FALLBACK.get(adong.slug, NEAREST_STATIONS_DEFAULT)
    nearest_stations = [
        {
            "rank": i + 1,
            "name": s["name"],
            "line": s["line"],
            "walking_min": s["walking_min"],
            "walking_distance_m": s["walking_distance_m"],
        }
        for i, s in enumerate(stations_raw[:3])
    ]

    # 버스: stop_count = transit / 2 정도, route는 그 ~3배
    stop_count = max(1, int(round(adong.score_transit / 2 + rng.uniform(-3, 3))))
    route_count = max(stop_count, int(round(stop_count * 3 + rng.uniform(-5, 5))))

    return {
        "nearest_stations": nearest_stations,
        "bus": {
            "stop_count": stop_count,
            "route_count": route_count,
        },
    }



def _build_similar_dongs(adong, all_dongs: Iterable) -> list[dict]:
    """
    SPEC 6.3 섹션 6 — 비슷한 동네 (시간 되면).
    POI 기반 임베딩은 9/10단계 작업. 현재는 raw 점수 3종 유클리드 거리 기반
    상위 3개로 더미 답.
    """
    others = [d for d in all_dongs if d.slug != adong.slug]
    if not others:
        return []

    def feat(x) -> tuple[float, float, float]:
        return (x.score_rent, x.score_amenity, x.score_transit)

    base_feat = feat(adong)
    scored = []
    for other in others:
        of = feat(other)
        # 정규화된 유클리드 거리 → 유사도 (0~100). max 거리는 sqrt(3*100^2) ≈ 173.2
        diff_sq = sum((a - b) ** 2 for a, b in zip(base_feat, of))
        dist = diff_sq ** 0.5
        max_dist = (3 * 100 ** 2) ** 0.5
        similarity = max(0.0, min(100.0, 100.0 * (1 - dist / max_dist)))
        scored.append((other, similarity))

    scored.sort(key=lambda t: t[1], reverse=True)
    top = scored[:3]
    return [
        {
            "slug": o.slug,
            "name": o.name,
            "gu": o.gu,
            "similarity_pct": round(sim, 1),
        }
        for o, sim in top
    ]


# ---------------------------------------------------------------------------
# 메인 빌더
# ---------------------------------------------------------------------------


def build_dummy_detail(adong, weights: dict, today: date | None = None) -> dict:
    """
    SPEC 6.3 동네 상세 응답 dict를 빌드.

    파라미터:
        adong: Adong 인스턴스 (centroid, score_*, area_km2 모두 채워져 있어야 함)
        weights: {"rent": 0~1, "amenity": 0~1, "transit": 0~1} 합 1
        today: 기준일 (테스트 주입용. 기본 date.today())

    반환: SPEC 6.3 정의 그대로의 snake_case dict.
    """
    if today is None:
        today = date.today()

    # ---- 종합 점수 ----
    # 7G-B1: Adong.composite_score 메서드 제거 → adong_surface.composite_score 함수 호출.
    score = round(
        _composite_score(
            adong,
            w_rent=weights["rent"],
            w_amenity=weights["amenity"],
            w_transit=weights["transit"],
        ),
        2,
    )

    # ---- 한 줄 요약 (raw 점수 기반, 가중치와 무관 — AdongSummary와 일관) ----
    summary = generate_summary(
        score_rent=adong.score_rent,
        score_amenity=adong.score_amenity,
        score_transit=adong.score_transit,
    )

    # ---- vs 서울 평균 ----
    vs_seoul_avg_pct = int(round(score - SEOUL_AVG_BASELINE))

    # ---- 중심점 ----
    centroid = {
        "lat": round(adong.centroid.y, 6) if adong.centroid else 0.0,
        "lng": round(adong.centroid.x, 6) if adong.centroid else 0.0,
    }

    # ---- 비슷한 동네 (전체 동 셋에서 top 3) ----
    # 7G-B1: Adong + current_score wrap. _build_similar_dongs는 slug/name/gu/score_*만 사용.
    all_dongs = [wrap(a) for a in build_adong_qs()]
    similar_dongs = _build_similar_dongs(adong, all_dongs)

    return {
        # 1. Hero
        "slug": adong.slug,
        "name": adong.name,
        "gu": adong.gu,
        "score": score,
        "summary": summary,
        "vs_seoul_avg_pct": vs_seoul_avg_pct,
        "centroid": centroid,

        # 2. 부동산
        "real_estate": _build_real_estate(adong, today),

        # 3. 편의시설
        "amenities": _build_amenities(adong),

        # 4. 교통
        "transit": _build_transit(adong),

        # 5. 비슷한 동네
        "similar_dongs": similar_dongs,
    }
