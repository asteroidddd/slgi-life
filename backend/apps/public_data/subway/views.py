"""
Subway 관련 뷰.

엔드포인트:
- GET /api/adongs/<slug>/transit-congestion
  → 대시보드 SPEC §4.4 섹션 C "시간대 혼잡도" 위젯 + §4.5 "동 성격 추정" 입력.
  → 지하철·버스 시간대별 평균 혼잡도 + 패턴 기반 personality 분류.

URL 등록은 apps.service.neighborhoods.urls 에서 한다 (adong-scoped URL 패턴 유지).
DB 스키마 변경 없음 — SELECT 전용. 신규 마이그레이션 없음.

성능:
- subway: SubwayCongestion 65k 행, NearestSubway 사전계산된 3개 역만 조회.
- bus: BusCongestion ~8M 행. BusStop.adong FK + 최근 N일 제한 (현재 데이터 31일).
  ANY(%s) station_ids/bus_stop_ids 기반 인덱스 활용.
- 캐시 5분 TTL.

이동 이력:
- sub-plan 2H: `apps.public_data.transit.views` → `apps.public_data.subway.views`로 이동.
  지하철·버스 혼합 view지만 personality 산정 시 subway 우선이며, NearestSubway가
  주 신호이므로 subway 앱에 둔다. 버스 모델은 apps.public_data.bus에서 import.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

# sub-plan 7G-B2 (결정 4A): NearestSubway(legacy) → NearestSubwayAdong 표면 치환.
# regions.Adong + Gu join. adong.code(=adong_code) ?? lock ??.
from apps.public_data.regions.models import Adong
from apps.public_data.subway.models import NearestSubwayAdong
from apps.public_data.bus.models import BusCongestion, BusStop  # noqa: F401  (BusCongestion is queried via raw SQL only)


# 가까운 역 N개 (NearestSubway 사전계산은 rank 1~3) — TOP 3 사용.
NEAREST_SUBWAY_N = 3

# BusCongestion 집계 기간 (일). 현재 RDS 적재 범위가 ~31일 (2026-03-12~04-11)이라
# 60일이어도 사실상 전체. 데이터가 더 누적되면 자연스럽게 윈도우로 동작.
BUS_RECENT_DAYS = 60

# day_type 매핑 — SubwayCongestion 에는 평일/토요일/일요일/휴일이 존재.
# "휴일"은 일요일과 같은 그룹으로 묶는다 (이중공휴일).
SUBWAY_DAY_BUCKETS: dict[str, str] = {
    "평일": "평일",
    "토요일": "토요일",
    "일요일": "일요일",
    "휴일": "일요일",
}
SUBWAY_DAY_KEYS = ("평일", "토요일", "일요일")
BUS_PATTERN_KEYS = ("평일", "주말")

# Personality 임계값 — SPEC §4.5.
RATIO_MORNING_TO_MIDDAY = 1.5    # 출퇴근 피크 강
RATIO_EVENING_TO_MIDDAY = 1.3    # 저녁 피크 강
RATIO_MIDDAY_TO_MORNING_HIGH = 0.8  # 낮 고른 분포
RATIO_WEEKEND_TO_WEEKDAY = 1.2   # 주말 피크 강


def _dong_header(adong: Adong) -> dict:
    """공통 adong 식별 dict — apps.service.neighborhoods.views._dong_header 와 동일 포맷.

    sub-plan 7G-B2: adong.gu(FK) → adong.gu.name. 응답 dict key 보존.
    """
    return {"slug": adong.slug, "name": adong.name, "gu": adong.gu.name}


def _empty_hours() -> list[dict]:
    """0~23시 빈 슬롯 (congestion=None)."""
    return [{"hour": h, "congestion": None} for h in range(24)]


def _fill_hours(rows: dict[int, float]) -> list[dict]:
    """{hour: avg} → 24슬롯 배열. 데이터 없는 시간은 None."""
    return [
        {"hour": h, "congestion": round(rows[h], 4) if h in rows else None}
        for h in range(24)
    ]


def _avg_over_hours(points: list[dict], start: int, end_inclusive: int) -> Optional[float]:
    """points[start..end_inclusive] 의 평균. None 슬롯 제외. 유효 슬롯 0이면 None."""
    vals = [
        p["congestion"]
        for p in points
        if start <= p["hour"] <= end_inclusive and p["congestion"] is not None
    ]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _avg_all(points: list[dict]) -> Optional[float]:
    """24시간 평균 (None 제외)."""
    vals = [p["congestion"] for p in points if p["congestion"] is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


# ---------------------------------------------------------------------------
# 데이터 수집
# ---------------------------------------------------------------------------


def _collect_subway(adong: Adong) -> dict:
    """가까운 지하철역 N개의 day_type x hour 평균 혼잡도.

    direction(상선/하선/내선/외선)·express_yn(일반/급행)은 전부 평균에 포함.
    "휴일" day_type 은 "일요일" 버킷으로 합쳐 일요일 평균 계산.

    sub-plan 7G-B2 (결정 4A):
    - legacy NearestSubway(neighborhoods.Adong FK) → NearestSubwayAdong(regions.Adong FK).
    - NearestSubwayAdong은 station FK 없이 station_name(비정규화)만 보유 →
      SubwayStation을 station_name으로 join하여 line/station_id 회수.
    - 응답 dict key (`stations` 안 `name`/`line`) 보존.
    """
    from apps.public_data.subway.models import SubwayStation

    ns_rows = list(
        NearestSubwayAdong.objects.filter(adong=adong)
        .order_by("rank")[:NEAREST_SUBWAY_N]
    )
    station_names = [ns.station_name for ns in ns_rows]
    stations_by_name: dict[str, list[SubwayStation]] = {name: [] for name in station_names}
    for station in SubwayStation.objects.filter(name__in=station_names).only("id", "name", "line"):
        stations_by_name.setdefault(station.name, []).append(station)

    stations_meta = []
    station_ids: list[str] = []
    for ns in ns_rows:
        matches = stations_by_name.get(ns.station_name) or []
        if not matches:
            stations_meta.append({"name": ns.station_name, "line": ""})
            continue
        lines: list[str] = []
        for st in matches:
            station_ids.append(st.id)
            if st.line not in lines:
                lines.append(st.line)
        stations_meta.append({"name": ns.station_name, "line": " / ".join(lines)})

    by_day: dict[str, list[dict]] = {k: _empty_hours() for k in SUBWAY_DAY_KEYS}

    if not station_ids:
        return {"stations": [], "by_day": by_day}

    # SQL 직접 — Django ORM 으로 EXTRACT(HOUR FROM time) 그루핑은 번거롭다.
    # day_type 단위 평균을 받아 파이썬에서 "휴일→일요일" 매핑 + 동일 hour 재평균.
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT
              day_type,
              EXTRACT(HOUR FROM time)::int AS hr,
              AVG(congestion)::float       AS cong,
              COUNT(*)                     AS n
            FROM subway_congestion
            WHERE station_id = ANY(%s)
            GROUP BY day_type, EXTRACT(HOUR FROM time)
            """,
            [station_ids],
        )
        raw = cur.fetchall()  # [(day_type, hr, avg, n), ...]

    # 휴일과 일요일이 같은 버킷이 되면 가중 평균 (행 수 n 기준).
    # bucket[hr] = (sum_n*avg, total_n)
    bucket: dict[str, dict[int, list[float]]] = {k: {} for k in SUBWAY_DAY_KEYS}
    for day_type, hr, avg, n in raw:
        target = SUBWAY_DAY_BUCKETS.get(day_type)
        if target is None:
            continue
        slot = bucket[target].setdefault(hr, [0.0, 0])
        slot[0] += float(avg) * int(n)
        slot[1] += int(n)

    for day_key in SUBWAY_DAY_KEYS:
        merged: dict[int, float] = {}
        for hr, (s, n) in bucket[day_key].items():
            if n > 0:
                merged[hr] = s / n
        by_day[day_key] = _fill_hours(merged)

    return {"stations": stations_meta, "by_day": by_day}


def _collect_bus(adong: Adong) -> dict:
    """동에 매핑된 BusStop 들의 평일/주말 x hour 평균 혼잡도.

    최근 BUS_RECENT_DAYS 일로 윈도우 제한 (BRIN(date) 활용).
    DOW: PostgreSQL EXTRACT(DOW FROM date) — 0=일, 6=토. 0/6 → 주말.

    sub-plan 7G-B2: adong.code → adong.adong_code 직접 매칭 (값 동일).
    """
    bus_stop_ids = list(
        BusStop.objects.filter(adong=adong).values_list("id", flat=True)
    )
    stop_count = len(bus_stop_ids)
    by_pattern: dict[str, list[dict]] = {k: _empty_hours() for k in BUS_PATTERN_KEYS}

    if stop_count == 0:
        return {"stop_count": 0, "by_pattern": by_pattern}

    # 데이터 적재 시점이 미래(2026-04-11)이면 timezone.now() 기준 cutoff 가
    # 데이터를 다 비울 수 있다 — BRIN 인덱스를 위해 BusCongestion 의 MAX(date) 를
    # 기준으로 cutoff 잡는다. 데이터 실시간 적재로 바뀌면 자연스럽게 따라옴.
    with connection.cursor() as cur:
        cur.execute("SELECT MAX(date) FROM bus_congestion WHERE bus_stop_id = ANY(%s)", [bus_stop_ids])
        max_date_row = cur.fetchone()
        max_date = max_date_row[0] if max_date_row else None

        if max_date is None:
            return {"stop_count": stop_count, "by_pattern": by_pattern}

        cutoff = max_date - timedelta(days=BUS_RECENT_DAYS)

        cur.execute(
            """
            SELECT
              CASE WHEN EXTRACT(DOW FROM date) IN (0, 6) THEN 'weekend' ELSE 'weekday' END AS pat,
              EXTRACT(HOUR FROM time)::int AS hr,
              AVG(congestion)::float       AS cong
            FROM bus_congestion
            WHERE bus_stop_id = ANY(%s)
              AND date >= %s
              AND congestion IS NOT NULL
            GROUP BY 1, 2
            """,
            [bus_stop_ids, cutoff],
        )
        rows = cur.fetchall()

    weekday: dict[int, float] = {}
    weekend: dict[int, float] = {}
    for pat, hr, avg in rows:
        if pat == "weekend":
            weekend[hr] = float(avg)
        else:
            weekday[hr] = float(avg)

    by_pattern["평일"] = _fill_hours(weekday)
    by_pattern["주말"] = _fill_hours(weekend)
    return {"stop_count": stop_count, "by_pattern": by_pattern}


# ---------------------------------------------------------------------------
# Personality
# ---------------------------------------------------------------------------


def _personality(subway: dict, bus: dict) -> dict:
    """동 성격 추정 — SPEC §4.5.

    분류:
      - morning_peak / midday > 1.5 && evening_peak / midday > 1.3 → "주거 중심"
      - midday / morning_peak > 0.8                                → "상업·업무 중심"
      - weekend / 평일평균 > 1.2                                   → "유동인구 많음"
    우선순위: 유동인구 > 상업·업무 > 주거.
    조건이 모두 빗나가면 label=None.

    데이터 우선: subway by_day["평일"] (역 기반이 더 신뢰). 없으면 bus.
    weekend 비교는 같은 소스 내 평일 vs 주말.
    """
    # 후보 소스 — (평일points, 주말points-list, label, source)
    weekday_points: list[dict] = []
    weekend_points: list[dict] = []
    source: str = ""

    sw_weekday = subway["by_day"].get("평일", [])
    sw_has_data = any(p["congestion"] is not None for p in sw_weekday)
    if sw_has_data:
        weekday_points = sw_weekday
        # 토 + 일 합쳐서 주말 평균: hour 별 평균.
        sat = subway["by_day"].get("토요일", [])
        sun = subway["by_day"].get("일요일", [])
        merged = []
        for h in range(24):
            vals = [
                p["congestion"]
                for p in (sat[h:h + 1] + sun[h:h + 1])
                if p and p["congestion"] is not None
            ]
            merged.append({
                "hour": h,
                "congestion": (sum(vals) / len(vals)) if vals else None,
            })
        weekend_points = merged
        source = "subway"
    else:
        bus_weekday = bus["by_pattern"].get("평일", [])
        bus_has_data = any(p["congestion"] is not None for p in bus_weekday)
        if bus_has_data:
            weekday_points = bus_weekday
            weekend_points = bus["by_pattern"].get("주말", [])
            source = "bus"

    if not weekday_points:
        return {
            "label": None,
            "reason": None,
            "scores": {
                "morning_peak": None,
                "midday": None,
                "evening_peak": None,
                "weekend": None,
            },
        }

    morning = _avg_over_hours(weekday_points, 7, 9)
    midday = _avg_over_hours(weekday_points, 11, 14)
    evening = _avg_over_hours(weekday_points, 18, 20)
    weekend_avg = _avg_all(weekend_points) if weekend_points else None
    weekday_full_avg = _avg_all(weekday_points)

    scores = {
        "morning_peak": round(morning, 4) if morning is not None else None,
        "midday": round(midday, 4) if midday is not None else None,
        "evening_peak": round(evening, 4) if evening is not None else None,
        "weekend": round(weekend_avg, 4) if weekend_avg is not None else None,
    }

    label: Optional[str] = None
    reason: Optional[str] = None

    # 1) 유동인구 많음 — 주말 > 평일.
    if (
        weekend_avg is not None
        and weekday_full_avg is not None
        and weekday_full_avg > 0
        and weekend_avg / weekday_full_avg > RATIO_WEEKEND_TO_WEEKDAY
    ):
        label = "유동인구 많음"
        ratio = weekend_avg / weekday_full_avg
        reason = f"주말 평균 혼잡도가 평일 대비 약 {ratio:.1f}배 높음."

    # 2) 상업·업무 중심 — 낮 시간대가 출퇴근 피크에 근접.
    elif (
        midday is not None
        and morning is not None
        and morning > 0
        and midday / morning > RATIO_MIDDAY_TO_MORNING_HIGH
    ):
        label = "상업·업무 중심"
        ratio = midday / morning
        reason = (
            f"낮 시간대(11~14시) 혼잡도가 출근 피크(7~9시) 대비 "
            f"{ratio * 100:.0f}% 수준으로 고르게 높음."
        )

    # 3) 주거 중심 — 출퇴근 피크가 낮 대비 강하게 솟음.
    elif (
        morning is not None
        and midday is not None
        and evening is not None
        and midday > 0
        and morning / midday > RATIO_MORNING_TO_MIDDAY
        and evening / midday > RATIO_EVENING_TO_MIDDAY
    ):
        label = "주거 중심"
        m_ratio = morning / midday
        reason = f"출근 시간(7~9시) 혼잡도가 낮 시간대 대비 약 {m_ratio:.1f}배 높음."

    return {"label": label, "reason": reason, "scores": scores}


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["adongs"],
    summary="시간대 혼잡도 + 동 성격 추정 (대시보드 §4.4 섹션 C / §4.5)",
    description=(
        "행정동의 시간대별 평균 혼잡도를 지하철·버스 두 트랙으로 반환하고, "
        "평일·주말/낮·피크 비율을 기반으로 동 성격을 추정한다.\n\n"
        "- subway: NearestSubway 사전계산된 가까운 역 TOP 3 기준. "
        "day_type=평일/토요일/일요일 각 24시간 배열. 혼잡도 raw 값.\n"
        "- bus: BusStop.adong FK 매핑된 정류장 전체. 최근 60일 윈도우. "
        "by_pattern=평일/주말 각 24시간 배열. congestion null 행 제외.\n"
        "- personality: subway 우선, 없으면 bus. SPEC §4.5 분류 규칙."
    ),
)
class AdongTransitCongestionView(APIView):
    """
    GET /api/adongs/<slug>/transit-congestion

    응답:
      {
        "adong": {"slug": "...", "name": "...", "gu": "..."},
        "subway": {
          "stations": [{"name": "충무로", "line": "3호선"}, ...],
          "by_day": {
            "평일":   [{"hour": 0, "congestion": ...}, ...,  {"hour": 23, ...}],
            "토요일": [...],
            "일요일": [...]
          }
        },
        "bus": {
          "stop_count": 13,
          "by_pattern": {
            "평일": [{"hour": 0, "congestion": ...}, ...],
            "주말": [...]
          }
        },
        "personality": {
          "label": "주거 중심" | "상업·업무 중심" | "유동인구 많음" | null,
          "reason": "...",
          "scores": {
            "morning_peak": ..., "midday": ..., "evening_peak": ..., "weekend": ...
          }
        }
      }

    - hour: 0~23 정수. 30분 단위 raw 행은 같은 hour 로 평균에 합쳐짐.
    - congestion: raw 평균 (출처 단위 보존). 데이터 없는 슬롯은 null.
    - 캐시 5분 TTL (키: dong_transit_congestion:v1:<slug>).
    """

    def get(self, request: Request, slug: str) -> Response:
        # regions.Adong + Gu join.
        try:
            adong = Adong.objects.select_related("gu").get(slug=slug)
        except Adong.DoesNotExist as exc:
            raise NotFound({"detail": "동을 찾을 수 없습니다."}) from exc

        cache_key = f"dong_transit_congestion:v1:{slug}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        subway = _collect_subway(adong)
        bus = _collect_bus(adong)
        personality = _personality(subway, bus)

        data = {
            "adong": _dong_header(adong),
            "subway": subway,
            "bus": bus,
            "personality": personality,
        }

        cache.set(cache_key, data, timeout=300)  # 5분
        return Response(data, status=status.HTTP_200_OK)
