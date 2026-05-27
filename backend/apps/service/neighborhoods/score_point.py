"""
임의 지점(lat/lng) 커널 점수 계산 — SPEC 섹션 11 (점수), Phase 2a.

`POST /api/score/point` 의 핵심 로직.

설계 메모
----------
1. **카테고리별 Gaussian 가중합** (SPEC 11.2):
   - σ = 300m. 1km 이내 시설만 (성능 + 의미있는 영향 범위).
   - bbox 프리필터(`geom && ST_Expand(point, 0.012°)`) + `ST_DistanceSphere(geom, point) <= 1000m`
     로 GiST 인덱스 활용 (geography cast 회피, 실측 8x 빠름).
   - 카테고리별 GROUP BY 한 쿼리로 끝낸다.

2. **점수 정규화 (간단 옵션 채택)**:
   - 학부 데모 우선순위. 백분위 정규화는 raw 값과 Adong 분포가 같은 메트릭이어야 하나,
     커널 raw (Gaussian sum)와 동 단위 raw (log-scale 카운트 가중합)는 서로 다른 척도.
   - 채택: kernel raw → min-max 클램프 0~100. radius_counts 와 nearest 가 사용자에게
     충분한 직관 보충 신호.
   - 참고: handoff 20260503-phase0a-step4-scores.md — 동 분포 mean=50 std≈29.

3. **Rent 점수**:
   - 점이 속한 Adong 의 `score_rent` 그대로 사용 (이미 백분위 정규화 됨).
   - Adong 매핑 실패(서울 외) → 50.0 + warning 로그.

4. **Transit 점수**:
   - 가장 가까운 지하철역 → 거리 → walk_min (`distance_m / 80`).
   - subway closeness = max(0, 1 - dist_m/1000). (service scoring updater 와 동일 공식).
   - bus density = min(1, log1p(bus_count) / log1p(50)).
   - score = 0.6 * subway + 0.4 * bus → *100.

5. **Composite**:
   - 사용자 가중치 합이 1이 아니면 정규화 (`w_i / sum(w)`).
   - 음수 weight → 400 (View 에서 검증).

6. **Commute (옵션)**:
   - school 문자열 → 좌표 dict lookup → haversine 거리 → 22 km/h 평균 → 분.
   - 22 km/h: 지하철 + 환승 + 도보 평균 (학부 데모 정밀도).
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from django.contrib.gis.geos import Point
from django.db import connection

from apps.service.neighborhoods.adong_surface import build_adong_qs, wrap


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 상수 (SPEC 11.2)
# ---------------------------------------------------------------------------
KERNEL_SIGMA_M = 300.0  # Gaussian σ. SPEC 11.2.
RADIUS_M = 1000.0  # 1km 컷. 이론상 σ=300m 의 99% 신뢰구간(~3σ=900m) 직후.
# 1km 를 위도/경도 도(degree)로 환산한 안전 마진 (위도 0.009°≈1km, 경도 37°N 0.012°≈1.05km).
# bbox 프리필터(`geom && ST_Expand`)가 GiST 인덱스를 효과적으로 사용하도록.
RADIUS_DEG = 0.012
WALK_SPEED_M_PER_MIN = 80.0  # 분당 80m 도보 (SPEC + handoff 일치).
COMMUTE_SPEED_KM_PER_H = 22.0  # 지하철 + 환승 + 도보 평균 (학부 데모 추정).

# 사용자에게 보여줄 "주요" 카테고리 (SPEC 6.3 참조 + handoff 패턴).
# nearest 시설 1개씩 + radius_counts 키.
PRIMARY_CATEGORIES = ("convenience", "cafe", "hospital", "park", "mart", "pharmacy")

# 카테고리별 가중치 — service scoring updater 와 동일 (handoff 20260503-phase0a-step4-scores.md).
# 동 단위 점수와 동일 시그널 가중을 사용하여 "동 평균과 같은 의미" 의 raw 값을 만든다.
CATEGORY_WEIGHTS = {
    "convenience": 0.20,
    "hospital": 0.15,
    "mart": 0.10,
    "restaurant": 0.10,
    "cafe": 0.10,
    "studycafe": 0.10,
    "pharmacy": 0.10,
    "laundry": 0.05,
    "oliveyoung": 0.05,
    "park": 0.05,
}


# ---------------------------------------------------------------------------
# 학교 좌표 dict (SPEC 11 — 통학 시간 옵션)
# 자취생 인구가 많은 서울 주요 대학 10개 + 캡스톤 호스트 동국대.
# 좌표는 캠퍼스 정문/메인 출입구 부근 (구글맵 / vworld 수동 검증).
# ---------------------------------------------------------------------------
SCHOOL_COORDS: dict[str, tuple[float, float]] = {
    "동국대": (37.5586, 127.0001),  # 중구 필동
    "한양대": (37.5570, 127.0454),  # 성동구 행당동
    "고려대": (37.5894, 127.0322),  # 성북구 안암동
    "연세대": (37.5658, 126.9386),  # 서대문구 신촌동
    "서강대": (37.5510, 126.9410),  # 마포구 신수동
    "이화여대": (37.5618, 126.9469),  # 서대문구 대현동
    "홍익대": (37.5512, 126.9252),  # 마포구 상수동
    "서울대": (37.4602, 126.9520),  # 관악구 신림동
    "중앙대": (37.5052, 126.9571),  # 동작구 흑석동
    "건국대": (37.5403, 127.0793),  # 광진구 화양동
    "성균관대": (37.5878, 126.9933),  # 종로구 명륜동 (인사캠 기준)
    "경희대": (37.5965, 127.0524),  # 동대문구 회기동
    "외대": (37.5973, 127.0577),  # 동대문구 이문동 (한국외대)
    "한국외대": (37.5973, 127.0577),
    "시립대": (37.5840, 127.0581),  # 동대문구 전농동 (서울시립대)
    "서울시립대": (37.5840, 127.0581),
}


# ---------------------------------------------------------------------------
# Kernel — 카테고리별 Gaussian 가중합 + 카운트
# ---------------------------------------------------------------------------
def compute_amenity_kernel(lat: float, lng: float) -> dict[str, dict[str, float]]:
    """
    좌표 주변 1km 시설을 카테고리별로 SUM(exp(-d^2 / 2σ^2)) 와 카운트.

    반환: {category: {"score": float, "n": int}}
        - score: Gaussian 가중합 raw (σ=300m). 점수가 아니라 raw 시그널.
        - n: 1km 이내 카운트.

    GROUP BY 한 쿼리로 처리. GiST 인덱스 + ST_DWithin geography 컷이라 충분히 빠름.
    """
    # bbox 프리필터(`location && ST_Expand`) 가 GiST 인덱스를 활용 → seq scan 회피.
    # ST_DistanceSphere 는 geography cast 없이 좌표 거리(m)를 즉시 계산.
    # `ST_DWithin(geography, ...)` 는 amenity 의 GiST 가 geometry 라 효과 없음 (실측 8x 느림).
    # sub-plan 4.5D: schema.dbml amenity 컬럼명은 `location` (구 `geom`에서 변경).
    sql = """
        SELECT
            category,
            SUM(EXP(
                -POWER(
                    ST_DistanceSphere(location, ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)),
                    2
                ) / (2.0 * %(sigma_sq)s)
            )) AS score,
            COUNT(*) AS n
        FROM amenity
        WHERE location && ST_Expand(
                ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326),
                %(radius_deg)s
            )
          AND ST_DistanceSphere(
                location,
                ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)
            ) <= %(radius)s
        GROUP BY category
    """
    params = {
        "lng": lng,
        "lat": lat,
        "sigma_sq": KERNEL_SIGMA_M * KERNEL_SIGMA_M,
        "radius": RADIUS_M,
        "radius_deg": RADIUS_DEG,
    }
    with connection.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    return {row[0]: {"score": float(row[1] or 0.0), "n": int(row[2])} for row in rows}


def amenity_score_from_kernel(kernel: dict[str, dict[str, float]]) -> float:
    """
    카테고리별 raw → 가중합 → 0~100 스케일.

    raw_total = Σ w_c * log1p(score_c)  (service scoring updater 와 동일 log1p 패턴).
    raw_total 자체가 제한된 0~몇 사이 값이라 단순 곱+클램프로 0~100 매핑.

    스케일 캘리브레이션:
      - σ=300m 가우시안 sum 의 raw 상한은 카테고리당 ~30~40 (밀집 상권 기준).
      - log1p(40) ≈ 3.7 → 가중합 (sum w=1.0) raw_total ≤ 3.7.
      - 100 * (raw_total / 3.0) clamp(0, 100) → 충분히 dense 한 곳은 100, 한적한 곳은 0.

    학부 데모 정밀도 OK. 정확한 동 분포 백분위 매핑은 future work.
    """
    total = 0.0
    for cat, w in CATEGORY_WEIGHTS.items():
        raw = kernel.get(cat, {}).get("score", 0.0)
        total += w * math.log1p(raw)

    SCALE = 3.0  # 100점 기준선 (raw_total = 3.0 일 때 100점).
    return max(0.0, min(100.0, (total / SCALE) * 100.0))


# ---------------------------------------------------------------------------
# Transit — 지하철 + 버스
# ---------------------------------------------------------------------------
def compute_transit(
    lat: float, lng: float
) -> tuple[float, Optional[dict[str, object]], int]:
    """
    Transit 점수 + 가장 가까운 지하철역 + 1km 버스 정류장 수.

    반환:
      - transit_score (0~100)
      - nearest_subway dict {name, line, distance_m, walk_min} 또는 None
      - bus_count (int)

    PostGIS raw SQL — 지하철은 KNN GiST, 버스는 ST_DWithin + COUNT.
    """
    # subway: KNN GiST(<->) + sphere distance 로 정확 미터 계산.
    # 527개 row 라 KNN <-> 가 즉시 반환 (≤10ms).
    # sub-plan 4.5D: schema.dbml subway_station / bus_stop 컬럼명은 `location`.
    nearest_sql = """
        SELECT name, line,
            ST_DistanceSphere(location, ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326))
                AS distance_m
        FROM subway_station
        ORDER BY location <-> ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)
        LIMIT 1
    """
    # bus: bbox 프리필터 + sphere 거리 (geography cast 회피).
    # bus_stop.location은 NULL 허용 (schema.dbml line 249) → NOT NULL 필터.
    bus_sql = """
        SELECT COUNT(*) FROM bus_stop
        WHERE location IS NOT NULL
          AND location && ST_Expand(
                ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326),
                %(radius_deg)s
            )
          AND ST_DistanceSphere(
                location, ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)
            ) <= %(radius)s
    """
    with connection.cursor() as cur:
        cur.execute(nearest_sql, {"lng": lng, "lat": lat})
        row = cur.fetchone()
        if row:
            sub_name, sub_line, sub_dist = row[0], row[1], float(row[2])
        else:
            sub_name = sub_line = None
            sub_dist = float("inf")

        cur.execute(
            bus_sql,
            {"lng": lng, "lat": lat, "radius": RADIUS_M, "radius_deg": RADIUS_DEG},
        )
        bus_count = int(cur.fetchone()[0])

    # 점수 계산 — service scoring updater 와 동일 공식 (Step 4 handoff).
    if math.isinf(sub_dist):
        subway_signal = 0.0
        nearest = None
    else:
        subway_signal = max(0.0, 1.0 - sub_dist / 1000.0)
        nearest = {
            "category": "subway",
            "name": sub_name,
            "line": sub_line,
            "distance_m": int(round(sub_dist)),
            "walk_min": max(1, int(round(sub_dist / WALK_SPEED_M_PER_MIN))),
        }

    bus_signal = min(1.0, math.log1p(bus_count) / math.log1p(50))

    transit_score = (0.6 * subway_signal + 0.4 * bus_signal) * 100.0
    return transit_score, nearest, bus_count


# ---------------------------------------------------------------------------
# Rent — Adong score 활용
# ---------------------------------------------------------------------------
def compute_rent_score(lat: float, lng: float) -> tuple[float, Optional[object]]:
    """
    포인트가 속한 행정동의 score_rent 를 그대로 반환.

    행정동 매핑 실패 → 50.0 (중간값) + warning.

    7G-B1: legacy Adong(geom 컬럼) → Adong(boundary 컬럼) + current_score 합성.
    공간 검색 인덱스: adong_boundary_gist_idx (regions.models.Adong.Meta.indexes).
    """
    point = Point(lng, lat, srid=4326)
    adong = build_adong_qs().filter(boundary__contains=point).first()
    if adong is None:
        logger.warning(
            "score_point: adong 매핑 실패 lat=%s lng=%s (서울 외 또는 경계). "
            "score_rent fallback=50.0",
            lat,
            lng,
        )
        return 50.0, None
    adong = wrap(adong)
    return float(adong.score_rent), adong


# ---------------------------------------------------------------------------
# Nearest 시설 — 카테고리별 1개씩 (1km 이내)
# ---------------------------------------------------------------------------
def find_nearest_per_category(
    lat: float, lng: float, categories: tuple[str, ...] = PRIMARY_CATEGORIES
) -> list[dict[str, object]]:
    """
    각 카테고리별 가장 가까운 시설 1개씩 (1km 이내). 없으면 skip.

    반환 list 는 walk_min 오름차순 정렬 (가까운 순).
    """
    # 한 쿼리로 카테고리별 nearest 1개씩 — DISTINCT ON 패턴.
    # 1km bbox 프리필터 + 카테고리 필터 + 카테고리별 KNN <-> 정렬 → 첫 row 만.
    # 카테고리당 별도 쿼리(N=6) 보다 6배 적은 왕복.
    # sub-plan 4.5D: schema.dbml amenity 컬럼명은 `location`.
    sql = """
        SELECT DISTINCT ON (category)
            category, name,
            ST_DistanceSphere(location, ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326))
                AS distance_m
        FROM amenity
        WHERE category = ANY(%(cats)s)
          AND location && ST_Expand(
                ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326),
                %(radius_deg)s
            )
          AND ST_DistanceSphere(
                location, ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)
            ) <= %(radius)s
        ORDER BY category,
                 location <-> ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)
    """
    with connection.cursor() as cur:
        cur.execute(
            sql,
            {
                "lng": lng,
                "lat": lat,
                "cats": list(categories),
                "radius": RADIUS_M,
                "radius_deg": RADIUS_DEG,
            },
        )
        rows = cur.fetchall()

    results: list[dict[str, object]] = []
    for category, name, dist in rows:
        results.append(
            {
                "category": category,
                "name": name,
                "walk_min": max(1, int(round(float(dist) / WALK_SPEED_M_PER_MIN))),
                "distance_m": int(round(float(dist))),
            }
        )
    results.sort(key=lambda d: d["walk_min"])
    return results


# ---------------------------------------------------------------------------
# Commute — school 옵션
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 사이 직선 거리 (km). 학부 데모 정밀도."""
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def compute_commute_min(lat: float, lng: float, school: str) -> Optional[int]:
    """
    학교명 → 좌표 → haversine 거리 → 통학 시간 (분).

    학교명을 못 찾으면 None.
    공식: dist_km / 22 km/h * 60 = min. + 5분 보정 (도보/환승 마진).
    """
    if not school:
        return None
    school_name = school.strip()
    school_lat = school_lng = None
    try:
        from apps.public_data.univ.models import Univ  # noqa: WPS433

        univ = (
            Univ.objects.filter(name=school_name, location__isnull=False)
            .only("location")
            .first()
        )
        if univ and univ.location:
            school_lat = univ.location.y
            school_lng = univ.location.x
    except Exception:  # pragma: no cover - fallback keeps point scoring available
        logger.exception("failed to lookup school from Univ DB")

    if school_lat is None or school_lng is None:
        coords = SCHOOL_COORDS.get(school_name)
        if coords is None:
            return None
        school_lat, school_lng = coords
    dist_km = haversine_km(lat, lng, school_lat, school_lng)
    minutes = int(round(dist_km / COMMUTE_SPEED_KM_PER_H * 60.0)) + 5
    return max(1, minutes)


# ---------------------------------------------------------------------------
# 메인 엔트리포인트
# ---------------------------------------------------------------------------
def compute_point_score(
    lat: float,
    lng: float,
    weights: dict[str, float],
    school: Optional[str] = None,
) -> dict[str, object]:
    """
    POST /api/score/point 의 핵심.

    weights: {"rent": 0~1, "amenity": 0~1, "transit": 0~1}.
        - View 에서 음수/누락 검증 후 정규화 (합 1.0) 한 값을 받음.

    반환 dict (응답 본문 그대로):
      {
        "score": 72.4,
        "breakdown": {"rent": 68.2, "amenity": 81.5, "transit": 70.1},
        "nearest": [{...}, ...],
        "radius_counts": {category: int, ...},
        "commute_min": 22 or null,
      }
    """
    # 1) 카테고리별 kernel raw (한 쿼리)
    kernel = compute_amenity_kernel(lat, lng)

    # 2) 각 축별 점수
    score_amenity = amenity_score_from_kernel(kernel)
    score_transit, nearest_subway, bus_count = compute_transit(lat, lng)
    score_rent, adong = compute_rent_score(lat, lng)

    # 3) Composite (가중치 정규화는 View 에서 처리)
    composite = (
        score_rent * weights["rent"]
        + score_amenity * weights["amenity"]
        + score_transit * weights["transit"]
    )

    # 4) Nearest 시설 — 지하철 1개 + 카테고리별 1개씩
    nearest_list: list[dict[str, object]] = []
    if nearest_subway is not None:
        nearest_list.append(nearest_subway)
    nearest_list.extend(find_nearest_per_category(lat, lng))

    # 5) radius_counts — 주요 카테고리만 (PRIMARY_CATEGORIES 키 보장)
    radius_counts: dict[str, int] = {}
    for cat in PRIMARY_CATEGORIES:
        radius_counts[cat] = int(kernel.get(cat, {}).get("n", 0))

    # 6) Commute (옵션)
    commute_min = compute_commute_min(lat, lng, school) if school else None

    return {
        "score": round(composite, 2),
        "breakdown": {
            "rent": round(score_rent, 2),
            "amenity": round(score_amenity, 2),
            "transit": round(score_transit, 2),
        },
        "nearest": nearest_list,
        "radius_counts": radius_counts,
        "commute_min": commute_min,
        # debug/observability
        "_meta": {
            "dong_slug": adong.slug if adong else None,
            "dong_name": f"{adong.gu} {adong.name}" if adong else None,
            "bus_count_1km": bus_count,
        },
    }
