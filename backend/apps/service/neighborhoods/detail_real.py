"""SPEC 6.3 동 상세 응답을 실 DB 데이터로 만드는 빌더.

Phase 4.5 후속. detail_dummy.build_dummy_detail 의 monthly_trend/recent_deals/
amenity counts/nearest_stations/bus stop_count 를 RentDeal/Amenity/NearestSubway/
BusStop 실 쿼리로 교체. similar_dongs 는 점수 기반 helper 를 재사용.
detail_dummy 의 helper 를 그대로 재사용.

응답 형식은 detail_dummy.build_dummy_detail 과 100% 동일 (AdongDetail 타입 호환).

RentDeal scope:
- Uses only rent_deal rows with confirmed adong_code for the current adong.
- Sparse or unmapped areas naturally return null/0 through the existing aggregations.
- NearestSubway: legacy(neighborhoods.Adong FK) → NearestSubwayAdong(regions.Adong FK).
  adong.code(adong_code) 매칭.
- BusStop.adong FK는 sub-plan 4.5B에서 정합 완료 (adong_id=adong.code).

응답 dict key 보존 (frontend lock 1).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Avg, Count, F, Min, Value

from apps.service.amenities.models import Amenity, AmenityAdong
from apps.public_data.rent_deal.models import (
    DEAL_TYPE_TO_HOUSING_TYPE,
    HOUSING_TYPE_TO_DEAL_TYPE,
    RentDeal,
)
from apps.public_data.bus.models import BusStop
from apps.public_data.subway.models import NearestSubwayAdong

from .adong_surface import build_adong_qs, composite_score as _composite_score, wrap
from .detail_dummy import (
    SEOUL_AVG_BASELINE,
    _amenity_level,
    _build_similar_dongs,
    _format_month,
    _round1,
)
from .summary import generate_summary


# ---------------------------------------------------------------------------
# Real-data helpers
# ---------------------------------------------------------------------------


# RentDeal.deal_type (영문 5종) → monthly_trend 차트 키.
# apt 는 차트 시리즈에 미포함이라 누락 — 응답에 키가 없어도 프론트는 무시.
TREND_KEYS = ("villa", "dagagu", "danok", "officetel")

# 자취 시장 필터 — 아파트는 매매성/가족 시장이라 자취 시세 감 잡기엔 노이즈.
# deposit 5억(=50000만원) 초과는 매매성 임대로 보고 제외.
STUDIO_DEAL_TYPES = ("villa", "dagagu", "danok", "officetel")
# sub-plan 4.5D: DB는 housing_type 한글. 응답 'deal_type'은 영문 enum 보존.
STUDIO_HOUSING_TYPES = tuple(
    DEAL_TYPE_TO_HOUSING_TYPE[k] for k in STUDIO_DEAL_TYPES
)
STUDIO_DEPOSIT_CAP = 50000  # 만원 단위 (= 5억)

# 유형 라벨 매핑 (영문 enum → 한글). 차트 라벨에 사용.
DEAL_TYPE_LABEL: dict[str, str] = {
    "villa": "연립다세대",
    "dagagu": "다가구",
    "danok": "단독",
    "officetel": "오피스텔",
}

# Amenity 11종 → SPEC 6.3 화면 8 카테고리 (한글 라벨).
# 병원·약국 은 hospital + pharmacy 합산. park/etc 는 화면 미노출.
AMENITY_DISPLAY: list[tuple[str, list[str], float]] = [
    # (label, internal_keys, density_target_weight — _build_amenities 와 동일 의도)
    ("편의점", ["convenience"], 0.95),
    ("카페", ["cafe"], 1.10),
    ("음식점", ["restaurant"], 1.40),
    ("마트", ["mart"], 0.30),
    ("병원·약국", ["hospital", "pharmacy"], 0.55),
    ("스터디카페", ["studycafe"], 0.25),
    ("세탁소", ["laundry"], 0.20),
    ("올리브영", ["oliveyoung"], 0.15),
]


def _real_real_estate(adong, today: date) -> dict:
    """SPEC 6.3 섹션 2 — 부동산 시세 (RentDeal SQL aggregation).

    RentDeal scope:
    - Uses only rent_deal rows with confirmed adong_code for the current adong.
    - Sparse or unmapped areas naturally return null/0 through the existing aggregations.
    """
    base_qs = RentDeal.objects.filter(adong_id=adong.code)

    # ---- 1) 최근 6개월 monthly_trend (housing_type별 평균 monthly_rent) ----
    # 6개월 전 1일 기준
    start_year, start_month = today.year, today.month - 5
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start = date(start_year, start_month, 1)

    # SQL: GROUP BY 월 + housing_type, 거래 3건 미만은 None
    # PG: TO_CHAR(contract_date, 'YYYY-MM')
    rows = list(
        base_qs.filter(contract_date__gte=start)
        .extra(select={"month": "TO_CHAR(contract_date, 'YYYY-MM')"})
        .values("month", "housing_type")
        .annotate(avg_rent=Avg("monthly_rent"), n=Count("id"))
    )
    # (month, deal_type 영문) → (avg, n). DB는 한글 housing_type → 영문 enum 매핑.
    by_key: dict[tuple[str, str], tuple[float, int]] = {}
    for r in rows:
        deal_type_en = HOUSING_TYPE_TO_DEAL_TYPE.get(r["housing_type"])
        if deal_type_en is None:
            continue
        by_key[(r["month"], deal_type_en)] = (float(r["avg_rent"] or 0), r["n"])

    # 6개월 month 라벨 만들기 (오래된 → 최신)
    months: list[str] = []
    cur = date(today.year, today.month, 1)
    seq: list[date] = []
    for _ in range(6):
        seq.append(cur)
        prev_month = cur.month - 1 or 12
        prev_year = cur.year if cur.month != 1 else cur.year - 1
        cur = date(prev_year, prev_month, 1)
    seq.reverse()
    months = [_format_month(d) for d in seq]

    monthly_trend = []
    for m in months:
        entry: dict = {"month": m}
        for key in TREND_KEYS:
            rec = by_key.get((m, key))
            # 거래 3건 미만 → null (SPEC 14.2)
            if rec is None or rec[1] < 3:
                entry[key] = None
            else:
                entry[key] = _round1(rec[0])
        monthly_trend.append(entry)

    # ---- 2) 보증금 대역별 평균 월세 ----
    # 5 대역: '0' (0~250), '500' (250~750), '1000' (750~1500),
    #        '2000' (1500~2500), '3000+' (2500+)
    # 거래 5건 미만 대역은 fallback (전체 동 평균 또는 0)
    BAND_RANGES = [
        ("0", 0, 250),
        ("500", 250, 750),
        ("1000", 750, 1500),
        ("2000", 1500, 2500),
        ("3000+", 2500, 10**9),
    ]
    deposit_band_avg = []
    for label, lo, hi in BAND_RANGES:
        agg = base_qs.filter(deposit__gte=lo, deposit__lt=hi).aggregate(
            avg=Avg("monthly_rent"), n=Count("id")
        )
        if agg["n"] and agg["n"] >= 5 and agg["avg"] is not None:
            avg = max(5.0, _round1(float(agg["avg"])))
        else:
            avg = 0.0  # 데이터 부족 — 프론트가 0이면 회색 처리
        deposit_band_avg.append({"band": label, "avg_monthly_rent": avg})

    # ---- 3) 자취 거래 베이스 쿼리셋 (apt 제외, 보증금 5억 이하, 최근 6개월) ----
    studio_qs = base_qs.filter(
        housing_type__in=STUDIO_HOUSING_TYPES,
        deposit__lte=STUDIO_DEPOSIT_CAP,
    )
    studio_recent_qs = studio_qs.filter(contract_date__gte=start)

    # ---- 3a) KPI 4종 (자취 시장 한눈에) ----
    converted_expr = F("monthly_rent") + F("deposit") * Value(0.005)
    kpi_agg = studio_recent_qs.aggregate(
        avg_rent=Avg(converted_expr),
        min_deposit=Min("deposit"),
        avg_area=Avg("area_m2"),
        n=Count("id"),
    )
    studio_kpi = {
        "avg_converted_rent": int(round(float(kpi_agg["avg_rent"]))) if kpi_agg["avg_rent"] is not None else None,
        "min_deposit": int(kpi_agg["min_deposit"]) if kpi_agg["min_deposit"] is not None else None,
        "avg_area_m2": _round1(float(kpi_agg["avg_area"])) if kpi_agg["avg_area"] is not None else None,
        "recent_count": int(kpi_agg["n"]),
    }

    # ---- 3b) 유형별 평균 환산월세 (가로 막대 차트용) ----
    type_avg_rows = list(
        studio_recent_qs.values("housing_type")
        .annotate(avg_converted=Avg(converted_expr), n=Count("id"))
    )
    # DB 한글 housing_type → 영문 enum 매핑 (응답 dict key 'deal_type' 보존).
    type_avg_map: dict[str, dict] = {}
    for r in type_avg_rows:
        en = HOUSING_TYPE_TO_DEAL_TYPE.get(r["housing_type"])
        if en is not None:
            type_avg_map[en] = r
    type_avg = []
    for key in STUDIO_DEAL_TYPES:
        rec = type_avg_map.get(key)
        if rec and rec["n"] >= 3:
            type_avg.append({
                "deal_type": key,
                "label": DEAL_TYPE_LABEL[key],
                "avg_converted_rent": int(round(float(rec["avg_converted"]))),
                "count": rec["n"],
            })
        else:
            # 거래 부족 — null 로 표시 (프론트 회색 처리)
            type_avg.append({
                "deal_type": key,
                "label": DEAL_TYPE_LABEL[key],
                "avg_converted_rent": None,
                "count": rec["n"] if rec else 0,
            })

    # ---- 3c) 면적-환산월세 산점도 (최근 6개월 자취 거래 sample 200건) ----
    # ORDER BY '?' 는 비싸서 최근 200건으로 단순화. 표본이 시점 편향되지만
    # 6개월 윈도우라 시즌성 영향 작음. area_m2 NULL 제외 (응답 dict 정합).
    scatter_rows = (
        studio_recent_qs.filter(area_m2__isnull=False)
        .order_by("-contract_date")
        .values("housing_type", "area_m2", "monthly_rent", "deposit")[:200]
    )
    scatter = []
    for r in scatter_rows:
        deal_type_en = HOUSING_TYPE_TO_DEAL_TYPE.get(r["housing_type"])
        if deal_type_en is None:
            continue
        converted = int(round(float(r["monthly_rent"]) + float(r["deposit"]) * 0.005))
        scatter.append({
            "deal_type": deal_type_en,
            "area_m2": _round1(float(r["area_m2"])),
            "converted_rent": converted,
        })

    # ---- 3d) 최근 자취 거래 5건 (apt 제외) ----
    recent_qs = (
        studio_qs.order_by("-contract_date", "-id")
        .values("contract_date", "housing_type", "area_m2", "deposit", "monthly_rent")[:5]
    )
    recent_deals = []
    for r in recent_qs:
        # type label은 한글 housing_type 그대로(응답 dict 'type' 보존).
        type_label = r["housing_type"]
        area_val = (
            _round1(float(r["area_m2"])) if r["area_m2"] is not None else None
        )
        recent_deals.append({
            "date": r["contract_date"].isoformat(),
            "type": type_label,
            "area_m2": area_val,
            "deposit": int(r["deposit"]),
            "monthly_rent": int(r["monthly_rent"]),
        })

    return {
        "monthly_trend": monthly_trend,
        "deposit_band_avg": deposit_band_avg,
        "recent_deals": recent_deals,
        "studio_kpi": studio_kpi,
        "type_avg": type_avg,
        "scatter": scatter,
    }


def _real_amenities(adong) -> list[dict]:
    """SPEC 6.3 섹션 3 — 8 카테고리 카운트 + 카테고리별 실 카운트 percentile.

    sub-plan 4C: Amenity.adong FK 제거에 따라 AmenityAdong N:M join 사용.
    응답 dict key — {"category", "count", "density_per_km2", "percentile", "level"}.
    percentile: 카테고리별 실 카운트 기반 TOP X% (1=최상위, 100=최하위). NULL=산출 불가.
    """
    from apps.public_data.regions.models import Adong  # noqa: WPS433

    counts: dict[str, int] = defaultdict(int)
    qs = (
        AmenityAdong.objects.filter(adong=adong.code)
        .values(category=F("amenity__category"))
        .annotate(n=Count("amenity_id"))
    )
    for r in qs:
        counts[r["category"]] = r["n"]

    all_qs = (
        AmenityAdong.objects.values(
            adong_code=F("adong_id"),
            category=F("amenity__category"),
        )
        .annotate(n=Count("amenity_id"))
    )
    counts_by_label: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in all_qs:
        for label, internal_keys, _w in AMENITY_DISPLAY:
            if r["category"] in internal_keys:
                counts_by_label[label][r["adong_code"]] += r["n"]
                break

    total_adong = Adong.objects.count()

    area = max(0.1, adong.area_km2 or 0.25)

    out = []
    for label, internal_keys, _weight in AMENITY_DISPLAY:
        cnt = sum(counts.get(k, 0) for k in internal_keys)
        density = round(cnt / area, 1)

        peer_counts: list[int] = list(counts_by_label.get(label, {}).values())
        zeros = max(0, total_adong - len(peer_counts))
        peer_counts.extend([0] * zeros)

        percentile: int | None
        if not peer_counts or max(peer_counts) == min(peer_counts):
            percentile = None
        else:
            lower = sum(1 for c in peer_counts if c < cnt)
            pct = (lower / len(peer_counts)) * 100
            percentile = max(1, min(100, round(100 - pct)))

        if percentile is None:
            level = "normal"
        elif percentile <= 33:
            level = "sufficient"
        elif percentile <= 66:
            level = "normal"
        else:
            level = "lacking"

        out.append({
            "category": label,
            "count": cnt,
            "density_per_km2": density,
            "percentile": percentile,
            "level": level,
        })
    return out


def _real_transit(adong) -> dict:
    """SPEC 6.3 섹션 4 — 가까운 역 top-3 + 버스 정류장 카운트.

    sub-plan 4.5D 정합:
    - legacy NearestSubway(neighborhoods.Adong FK) → NearestSubwayAdong(regions.Adong FK).
    - Adong.code(행정동 10자리) = Adong.adong_code, 직접 매칭.
    - station FK 제거 → station_name 비정규화 컬럼. line은 SubwayStation에서 lookup.
    """
    from apps.public_data.subway.models import SubwayStation  # noqa: WPS433

    # NearestSubwayAdong 사전계산 (compute_nearest_subway.py).
    rows = list(
        NearestSubwayAdong.objects.filter(adong_id=adong.code)
        .order_by("rank")[:3]
    )
    # 한꺼번에 line lookup. 같은 역명에 여러 호선이 있으면 모두 보존한다.
    names = [r.station_name for r in rows]
    lines_by_name: dict[str, list[str]] = {}
    if names:
        for s_name, s_line in SubwayStation.objects.filter(name__in=names).values_list(
            "name", "line"
        ):
            bucket = lines_by_name.setdefault(s_name, [])
            if s_line not in bucket:
                bucket.append(s_line)
    nearest_stations = []
    for ns in rows:
        # 도보 시간: 직선거리 / 70m/min (1.2배 우회 + 4.8km/h ≈ dummy 패턴 유지)
        walking_min = max(1, int(round(ns.distance_m / 70)))
        nearest_stations.append({
            "rank": ns.rank,
            "name": ns.station_name,
            "line": " / ".join(lines_by_name.get(ns.station_name) or ["-"]),
            "walking_min": walking_min,
            "walking_distance_m": int(round(ns.distance_m)),
        })
    # 데이터 부족 (rank=3 이 채워지지 않은 동) — 빈 슬롯은 정보 없음
    while len(nearest_stations) < 3:
        nearest_stations.append({
            "rank": len(nearest_stations) + 1,
            "name": "정보 없음",
            "line": "-",
            "walking_min": 0,
            "walking_distance_m": 0,
        })

    # 버스: stop_count = BusStop.adong=this. route_count는 노선정보 없으니 stop*3 추정.
    # sub-plan 4.5B 정합: BusStop.adong FK 제거 → adong FK (regions.Adong, PK=adong_code).
    # Adong.code (행정동 코드) == Adong.adong_code 이므로 adong_code로 직접 매칭.
    stop_count = BusStop.objects.filter(adong_id=adong.code).count()
    route_count = stop_count * 3  # 단순 추정 (노선 데이터 부재)

    return {
        "nearest_stations": nearest_stations,
        "bus": {
            "stop_count": stop_count,
            "route_count": route_count,
        },
    }


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------


def build_real_detail(adong, weights: dict, today: date | None = None) -> dict:
    """SPEC 6.3 동네 상세 응답 dict — 실 DB 쿼리 기반.

    detail_dummy.build_dummy_detail 과 응답 키/형식 100% 동일. 차이는 값이
    실 DB 에서 계산된다는 점:
    - real_estate.monthly_trend: RentDeal SQL GROUP BY 월/deal_type
    - real_estate.deposit_band_avg: RentDeal 보증금 구간 GROUP BY
    - real_estate.recent_deals: RentDeal 최근 5건
    - amenities: Amenity GROUP BY category (8 카테고리 매핑)
    - transit.nearest_stations: NearestSubway 사전계산
    - transit.bus.stop_count: BusStop count (route_count 는 stop*3 추정)
    - similar_dongs: 점수 기반 detail_dummy helper 재사용
    """
    if today is None:
        today = date.today()

    # ---- Hero (Adong 컬럼 직접) ----
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
    summary = generate_summary(
        score_rent=adong.score_rent,
        score_amenity=adong.score_amenity,
        score_transit=adong.score_transit,
    )
    vs_seoul_avg_pct = int(round(score - SEOUL_AVG_BASELINE))
    centroid = {
        "lat": round(adong.centroid.y, 6) if adong.centroid else 0.0,
        "lng": round(adong.centroid.x, 6) if adong.centroid else 0.0,
    }

    # ---- 비슷한 동네 (점수 기반, dummy helper 재사용) ----
    # 7G-B1: Adong + current_score 합성 후 wrap. _build_similar_dongs는 slug/name/gu/
    # score_* 만 사용 → wrap 객체 호환.
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
        # 2. 부동산 (실)
        "real_estate": _real_real_estate(adong, today),
        # 3. 편의시설 (실)
        "amenities": _real_amenities(adong),
        # 4. 교통 (실)
        "transit": _real_transit(adong),
        # 5. 리뷰 (데이터 없음 — dummy 그대로)
        # 6. 비슷한 동네 (점수 기반)
        "similar_dongs": similar_dongs,
    }
