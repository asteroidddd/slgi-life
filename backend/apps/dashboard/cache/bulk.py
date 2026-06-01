from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.db import connection
from django.utils import timezone

from apps.public_data.rent_deal.utils import get_annual_conversion_rate, get_monthly_conversion_rate

CACHE_SOURCE_VERSION = "dashboard-cache-bulk-v4"

SAFETY_GRADE_METRICS = [
    ("SAFETY_GRADE_TRAFFIC", "교통사고"),
    ("SAFETY_GRADE_FIRE", "화재"),
    ("SAFETY_GRADE_CRIME", "범죄"),
    ("SAFETY_GRADE_LIFE", "생활안전"),
    ("SAFETY_GRADE_SUICIDE", "자살"),
    ("SAFETY_GRADE_DISEASE", "감염병"),
]

INFRA_GROUPS = [
    {"key": "food", "label": "식생활", "categories": ["restaurant", "cafe", "convenience", "mart", "nightlife"]},
    {"key": "culture", "label": "문화", "categories": ["park", "gym", "beauty", "oliveyoung", "laundry"]},
    {"key": "study", "label": "학습", "categories": ["library", "book_stationery", "study_cafe"]},
    {"key": "medical", "label": "의료", "categories": ["hospital", "dental", "pharmacy"]},
]
for group in INFRA_GROUPS:
    if group["key"] == "food" and "daiso" not in group["categories"]:
        group["categories"].insert(group["categories"].index("mart") + 1, "daiso")
VISUAL_CATEGORIES = [category for group in INFRA_GROUPS for category in group["categories"]]
FOOD_CATEGORIES = ["restaurant", "cafe", "convenience", "mart", "daiso", "nightlife"]
MEDICAL_CATEGORIES = ["pharmacy", "hospital", "dental"]
CATEGORY_LABELS = {
    "daiso": "다이소",
    "convenience": "편의점",
    "mart": "슈퍼마켓",
    "restaurant": "음식점",
    "cafe": "카페",
    "hospital": "병원",
    "dental": "치과",
    "pharmacy": "약국",
    "park": "공원",
    "library": "도서관",
    "nightlife": "주점",
    "gym": "헬스장",
    "beauty": "미용",
    "laundry": "세탁",
    "book_stationery": "서점/문구",
    "study_cafe": "스터디카페/독서실",
    "oliveyoung": "올리브영",
}
DAY_BY_WEEKDAY = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass(frozen=True)
class RegionConfig:
    region_type: str
    table: str
    code_col: str
    score_table: str
    amenity_link_table: str
    park_link_table: str
    cache_relation: str


CONFIGS = {
    "adong": RegionConfig("adong", "adong", "adong_code", "current_adong", "amenity_adong", "park_adong", "adong"),
    "ldong": RegionConfig("ldong", "ldong", "ldong_code", "current_ldong", "amenity_ldong", "park_ldong", "ldong"),
}


def fetchall(sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetchone(sql: str, params: list[Any] | None = None) -> dict[str, Any]:
    rows = fetchall(sql, params)
    return rows[0] if rows else {}


def as_float(value: Any, digits: int | None = None) -> float | None:
    if value is None:
        return None
    out = float(value)
    return round(out, digits) if digits is not None else out


def as_int(value: Any) -> int:
    return int(value or 0)


def metric(key: str, label: str, value: Any, unit: str = "", *, tone: str = "info", badge: str = "", description: str = "") -> dict[str, Any]:
    return {"key": key, "label": label, "value": value, "unit": unit, "tone": tone, "badge": badge, "description": description}


def quicktake(label: str, tone: str = "info") -> dict[str, str]:
    return {"label": label, "tone": tone}


def pct_delta(value: float | None, base: float | None) -> float | None:
    if value is None or base in (None, 0):
        return None
    return (value - base) / base


def tone_from_delta(delta: float | None, *, higher_is_bad: bool = False, threshold: float = 0.1) -> str:
    if delta is None or abs(delta) < threshold:
        return "info"
    high = delta > 0
    if higher_is_bad:
        return "bad" if high else "good"
    return "good" if high else "bad"


def fmt_delta(delta: float | None, base_label: str = "서울 평균") -> str:
    if delta is None:
        return f"{base_label} 비교값 없음"
    return f"{base_label} 대비 {'+' if delta >= 0 else ''}{delta * 100:.1f}%"


def density(count: int | float | None, area_km2: float | None) -> float | None:
    if count is None or not area_km2:
        return None
    return float(count) / float(area_km2)


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def add_months(value: date, delta: int) -> date:
    month_index = value.year * 12 + value.month - 1 + delta
    return date(month_index // 12, month_index % 12 + 1, 1)


def month_labels(start: date, months: int) -> list[str]:
    return [add_months(start, index).strftime("%Y-%m") for index in range(months)]


def week_labels(start: date, end: date) -> list[str]:
    current = start - timedelta(days=start.weekday())
    labels: list[str] = []
    while current <= end:
        labels.append(current.isoformat())
        current += timedelta(days=7)
    return labels


def service_minute(time_text: str, *, mode: str) -> int:
    hour, minute = [int(part) for part in time_text.split(":")]
    total = hour * 60 + minute
    start = 330 if mode == "subway" else 240
    if total < start:
        total += 1440
    return total


def display_time(minutes: int) -> str:
    hour = (minutes // 60) % 24
    minute = minutes % 60
    text = f"{hour:02d}:{minute:02d}"
    return f"익일 {text}" if minutes >= 1440 else text


def empty_overview(region: dict[str, Any], headline: str, summary: str) -> dict[str, Any]:
    return {"region": region, "headline": headline, "summary": summary, "quicktakes": [], "metrics": [], "basis": {}}


@lru_cache(maxsize=2)
def load_intro_map(region_type: str) -> dict[tuple[str, str], str]:
    filename = "dong_intro_adong.csv" if region_type == "adong" else "dong_intro_ldong.csv"
    path = Path(__file__).resolve().parents[3] / "data" / filename
    rows: dict[tuple[str, str], str] = {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                gu_name = (row.get("gu_name") or "").strip()
                dong_name = (row.get("dong_name") or "").strip()
                intro = (row.get("intro") or "").strip()
                if gu_name and dong_name and intro:
                    rows[(gu_name, dong_name)] = intro
    except FileNotFoundError:
        return {}
    return rows


def build_intro(region: dict[str, Any]) -> str:
    intro = load_intro_map(region["type"]).get((region["gu_name"], region["dong_name"]))
    if intro:
        return intro
    return (
        f"{region['gu_name']} {region['dong_name']}의 거래 시세, 교통 접근성, 생활 인프라, "
        "안전 지표를 서울 평균 기준으로 정리했습니다."
    )


def load_regions(config: RegionConfig, *, limit: int | None = None, offset: int = 0) -> dict[str, dict[str, Any]]:
    limit_sql = "LIMIT %s" if limit else ""
    offset_sql = "OFFSET %s" if offset else ""
    params: list[Any] = []
    if limit:
        params.append(limit)
    if offset:
        params.append(offset)
    rows = fetchall(
        f"""
        SELECT
            r.{config.code_col} AS code,
            r.slug,
            r.name AS dong_name,
            g.gu_code,
            g.name AS gu_name,
            (r.area_m2::float / 1000000.0) AS area_km2,
            ARRAY[
                ST_XMin(Box2D(r.boundary)),
                ST_YMin(Box2D(r.boundary)),
                ST_XMax(Box2D(r.boundary)),
                ST_YMax(Box2D(r.boundary))
            ] AS bbox,
            c.score_rent,
            c.score_amenity,
            c.score_transit,
            c.score_safety,
            c.score_total,
            c.rank_safety
        FROM {config.table} r
        JOIN gu g ON g.gu_code = r.gu_code
        LEFT JOIN {config.score_table} c ON c.{config.code_col} = r.{config.code_col}
        ORDER BY g.name, r.name
        {limit_sql} {offset_sql}
        """,
        params,
    )
    regions: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = row["code"]
        bbox = [float(value) for value in row["bbox"]] if row.get("bbox") else None
        region = {
            "type": config.region_type,
            "code": code,
            "slug": row["slug"] or "",
            "gu_code": row["gu_code"],
            "gu_name": row["gu_name"],
            "dong_name": row["dong_name"],
            "area_km2": as_float(row["area_km2"]),
            "bbox": bbox,
        }
        regions[code] = {
            "region": region,
            "scores": {
                "score_rent": as_float(row.get("score_rent"), 1),
                "score_amenity": as_float(row.get("score_amenity"), 1),
                "score_transit": as_float(row.get("score_transit"), 1),
                "score_safety": as_float(row.get("score_safety"), 1),
                "score_total": as_float(row.get("score_total"), 1),
                "rank_safety": row.get("rank_safety"),
            },
        }
    return regions


def build_rent_parts(config: RegionConfig, regions: dict[str, dict[str, Any]], *, months: int = 6) -> dict[str, dict[str, Any]]:
    codes = list(regions)
    if not codes:
        return {}
    max_contract = fetchone("SELECT max(contract_date) AS max_date FROM rent_deal").get("max_date") or timezone.localdate()
    start = add_months(month_start(max_contract), -(months - 1))
    labels = month_labels(start, months)
    trend_labels = week_labels(start, max_contract)
    monthly_rate = get_monthly_conversion_rate()
    annual_rate = get_annual_conversion_rate()
    basis = {
        "period_months": months,
        "conversion_rate": annual_rate,
        "conversion_rate_source": "한국부동산원 서울 최근 전월세전환율 평균",
        "comparison": "서울 전체 기준 비교",
    }
    seoul = fetchone(
        """
        SELECT COUNT(*)::int AS deal_count,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY monthly_rent + deposit * %s) AS median_converted_rent,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY area_m2) AS median_area,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY (monthly_rent + deposit * %s) / NULLIF(area_m2, 0)) AS median_rent_per_area
        FROM rent_deal
        WHERE contract_date >= %s AND area_m2 IS NOT NULL AND area_m2 > 0
        """,
        [monthly_rate, monthly_rate, start],
    )
    seoul_avg_count = (as_float(seoul.get("deal_count")) or 0) / max(1, len(regions))
    stats = {
        row["code"]: row
        for row in fetchall(
            f"""
            SELECT {config.code_col} AS code,
                   COUNT(*)::int AS deal_count,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY monthly_rent + deposit * %s) AS median_converted_rent,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY area_m2) AS median_area,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY (monthly_rent + deposit * %s) / NULLIF(area_m2, 0)) AS median_rent_per_area
            FROM rent_deal
            WHERE contract_date >= %s
              AND {config.code_col} = ANY(%s)
              AND area_m2 IS NOT NULL AND area_m2 > 0
            GROUP BY {config.code_col}
            """,
            [monthly_rate, monthly_rate, start, codes],
        )
    }
    monthly_counts: dict[str, dict[str, int]] = defaultdict(dict)
    for row in fetchall(
        f"""
        SELECT {config.code_col} AS code, to_char(date_trunc('month', contract_date), 'YYYY-MM') AS month, COUNT(*)::int AS count
        FROM rent_deal
        WHERE contract_date >= %s AND {config.code_col} = ANY(%s)
        GROUP BY {config.code_col}, 2
        """,
        [start, codes],
    ):
        monthly_counts[row["code"]][row["month"]] = row["count"]

    trend_values: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for row in fetchall(
        f"""
        WITH type_counts AS (
            SELECT {config.code_col} AS code, housing_type, COUNT(*) AS cnt
            FROM rent_deal
            WHERE contract_date >= %s AND {config.code_col} = ANY(%s) AND housing_type IS NOT NULL
            GROUP BY {config.code_col}, housing_type
        ), ranked AS (
            SELECT *, row_number() OVER (PARTITION BY code ORDER BY cnt DESC, housing_type) AS rn
            FROM type_counts
        )
        SELECT r.{config.code_col} AS code,
               r.housing_type,
               to_char(date_trunc('week', r.contract_date)::date, 'YYYY-MM-DD') AS week,
               ROUND(AVG((r.monthly_rent + r.deposit * %s) / NULLIF(r.area_m2, 0))::numeric, 2)::float AS value
        FROM rent_deal r
        JOIN ranked t ON t.code = r.{config.code_col} AND t.housing_type = r.housing_type AND t.rn <= 5
        WHERE r.contract_date >= %s AND r.{config.code_col} = ANY(%s) AND r.area_m2 IS NOT NULL AND r.area_m2 > 0
        GROUP BY r.{config.code_col}, r.housing_type, 3
        ORDER BY r.{config.code_col}, r.housing_type, 3
        """,
        [start, codes, monthly_rate, start, codes],
    ):
        trend_values[row["code"]][row["housing_type"]][row["week"]] = as_float(row["value"], 2)

    mix_counts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    totals: dict[str, int] = defaultdict(int)
    for row in fetchall(
        f"""
        SELECT {config.code_col} AS code, housing_type, COUNT(*)::int AS count
        FROM rent_deal
        WHERE contract_date >= %s AND {config.code_col} = ANY(%s) AND housing_type IS NOT NULL
        GROUP BY {config.code_col}, housing_type
        ORDER BY {config.code_col}, count DESC, housing_type
        """,
        [start, codes],
    ):
        totals[row["code"]] += row["count"]
        mix_counts[row["code"]].append({"housing_type": row["housing_type"], "count": row["count"]})

    out: dict[str, dict[str, Any]] = {}
    for code, wrapper in regions.items():
        region = wrapper["region"]
        row = stats.get(code, {})
        deal_count = as_int(row.get("deal_count"))
        volume_delta = pct_delta(float(deal_count), seoul_avg_count)
        cost_delta = pct_delta(as_float(row.get("median_converted_rent")), as_float(seoul.get("median_converted_rent")))
        price_delta = pct_delta(as_float(row.get("median_rent_per_area")), as_float(seoul.get("median_rent_per_area")))
        area_delta = pct_delta(as_float(row.get("median_area")), as_float(seoul.get("median_area")))
        weekly_area_values = [
            value
            for week in trend_labels
            for type_values in trend_values.get(code, {}).values()
            for value in [type_values.get(week)]
            if value is not None
        ]
        trend_delta = pct_delta(weekly_area_values[-1], weekly_area_values[0]) if len(weekly_area_values) >= 2 else None
        volume_tone = tone_from_delta(volume_delta, threshold=0.12)
        cost_tone = tone_from_delta(cost_delta, higher_is_bad=True, threshold=0.08)
        price_tone = tone_from_delta(price_delta, higher_is_bad=True, threshold=0.08)
        area_tone = "info" if area_delta is None or abs(area_delta) < 0.1 else "good" if area_delta > 0 else "info"
        trend_tone = tone_from_delta(trend_delta, higher_is_bad=True, threshold=0.05)
        volume_label = "거래 활발" if volume_tone == "good" else "거래 적음" if volume_tone == "bad" else "거래 보통"
        cost_label = "가격 비쌈" if price_tone == "bad" else "가격 저렴" if price_tone == "good" else "가격 보통"
        monthly_label = "높음" if cost_tone == "bad" else "낮음" if cost_tone == "good" else "보통"
        area_label = "면적 넓음" if (area_delta or 0) > 0.1 else "면적 작음" if (area_delta or 0) < -0.1 else "면적 보통"
        trend_label = "상승세" if trend_tone == "bad" else "하락세" if trend_tone == "good" else "보합"
        summary = (
            f"㎡당 환산월세는 최근 {months}개월 거래를 주 단위로 나눠 봅니다. "
            f"가격은 서울 전체 기준보다 {'높은 편' if price_tone == 'bad' else '낮은 편' if price_tone == 'good' else '비슷한 편'}이고, "
            f"거래량은 서울 동 평균 대비 {volume_label}입니다."
        )
        volume_items = [{"month": month, "count": monthly_counts.get(code, {}).get(month, 0)} for month in labels]
        series = [
            {"housing_type": housing_type, "items": [{"week": week, "month": week, "value": values.get(week)} for week in trend_labels]}
            for housing_type, values in trend_values.get(code, {}).items()
        ]
        total_mix = max(1, totals.get(code, 0))
        mix_items = [
            {**item, "ratio": round(item["count"] / total_mix * 100, 1)}
            for item in mix_counts.get(code, [])
        ]
        overview = {
            "region": region,
            "headline": f"{cost_label}, {area_label}, {volume_label}",
            "summary": summary,
            "quicktakes": [
                quicktake(cost_label, price_tone),
                quicktake(area_label, area_tone),
                quicktake(volume_label, volume_tone),
                quicktake(trend_label, trend_tone),
            ],
            "metrics": [
                metric("converted_rent_per_area", "㎡당 환산월세", as_float(row.get("median_rent_per_area"), 2), "만원/㎡", tone=price_tone, badge=cost_label.replace("가격 ", ""), description=fmt_delta(price_delta, "서울 ㎡당 중위값")),
                metric("median_converted_monthly_rent", "중위 환산월세", as_float(row.get("median_converted_rent"), 1), "만원", tone=cost_tone, badge=monthly_label, description=fmt_delta(cost_delta, "서울 중위값")),
                metric("median_area", "중위 전용면적", as_float(row.get("median_area"), 1), "㎡", tone=area_tone, badge=area_label, description=fmt_delta(area_delta, "서울 중위값")),
                metric("deal_count_6m", f"최근 {months}개월 거래", deal_count, "건", tone=volume_tone, badge=volume_label.replace("거래 ", ""), description=fmt_delta(volume_delta, "서울 동 평균")),
            ],
            "basis": basis,
            "fallback": {"is_fallback": False, "level": None},
        }
        out[code] = {
            "region": region,
            "overview": overview,
            "volume_trend": {"region": region, "items": volume_items, "basis": {**basis, "max_monthly_count": max((item["count"] for item in volume_items), default=0)}},
            "rent_trend": {"region": region, "series": series, "basis": {**basis, "unit": "만원/㎡", "period": "week", "visual_scope": "region"}},
            "housing_type_mix": {"region": region, "items": mix_items, "basis": {**basis, "visual_scope": "region"}},
            "basis": basis,
        }
    return out


def build_transit_parts(config: RegionConfig, regions: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    codes = list(regions)
    if not codes:
        return {}
    total_area = sum(float(item["region"]["area_km2"] or 0) for item in regions.values()) or 1
    bus_counts = {row["code"]: row["count"] for row in fetchall(f"SELECT {config.code_col} AS code, COUNT(*)::int AS count FROM bus_stop WHERE {config.code_col} = ANY(%s) AND location IS NOT NULL GROUP BY {config.code_col}", [codes])}
    station_counts = {row["code"]: row["count"] for row in fetchall(f"SELECT {config.code_col} AS code, COUNT(DISTINCT name)::int AS count FROM subway_station WHERE {config.code_col} = ANY(%s) AND location IS NOT NULL GROUP BY {config.code_col}", [codes])}
    station_names: dict[str, list[str]] = defaultdict(list)
    station_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    nearest_table = "nearest_subway_adong" if config.region_type == "adong" else "nearest_subway_ldong"
    for row in fetchall(
        f"""
        SELECT n.{config.code_col} AS code,
               n.station_name AS name,
               MIN(n.distance_m)::float AS distance_m,
               array_remove(array_agg(DISTINCT s.line ORDER BY s.line), NULL) AS lines
        FROM {nearest_table} n
        LEFT JOIN subway_station s ON s.name = n.station_name
        WHERE n.{config.code_col} = ANY(%s)
          AND n.station_name IS NOT NULL
          AND n.station_name <> ''
          AND n.distance_m <= 1000.0
        GROUP BY n.{config.code_col}, n.station_name
        ORDER BY n.{config.code_col}, MIN(n.distance_m), n.station_name
        """,
        [codes],
    ):
        station_names[row["code"]].append(row["name"])
        station_items[row["code"]].append(
            {
                "name": row["name"],
                "distance_m": as_float(row.get("distance_m"), 0),
                "lines": row.get("lines") or [],
            }
        )
    seoul_bus_density = sum(bus_counts.values()) / total_area
    seoul_station_density = sum(station_counts.values()) / total_area
    subway_rows = fetchall(
        f"""
        WITH nearby AS (
            SELECT n.{config.code_col} AS code,
                   n.station_name,
                   MIN(n.distance_m)::float AS distance_m
            FROM {nearest_table} n
            WHERE n.{config.code_col} = ANY(%s)
              AND n.station_name IS NOT NULL
              AND n.station_name <> ''
              AND n.distance_m <= 1000.0
            GROUP BY n.{config.code_col}, n.station_name
        ),
        normalized AS (
            SELECT n.code,
                   CASE WHEN c.day_type = '평일' THEN '평일' ELSE '주말' END AS day_type,
                   c.time,
                   c.congestion::float AS congestion,
                   (1.0 / (GREATEST(n.distance_m, 0.0) + 200.0)) AS weight
            FROM nearby n
            JOIN subway_station s ON s.name = n.station_name
            JOIN subway_congestion c ON s.id = c.station_id::text
        )
        SELECT code, day_type, to_char(time, 'HH24:MI') AS time,
               ROUND((SUM(congestion * weight) / NULLIF(SUM(weight), 0))::numeric, 1)::float AS congestion
        FROM normalized
        GROUP BY code, day_type, time
        """,
        [codes],
    )
    bus_rows = fetchall(
        f"""
        SELECT b.{config.code_col} AS code,
               CASE WHEN EXTRACT(ISODOW FROM c.date)::int IN (6, 7) THEN '주말' ELSE '평일' END AS day_type,
               to_char(c.time, 'HH24:MI') AS time,
               ROUND(AVG(c.congestion)::numeric, 1)::float AS congestion
        FROM bus_congestion c
        JOIN bus_stop b ON b.id = c.bus_stop_id::text
        WHERE b.{config.code_col} = ANY(%s) AND b.location IS NOT NULL
        GROUP BY b.{config.code_col}, day_type, c.time
        """,
        [codes],
    )
    grouped: dict[str, dict[tuple[str, str], list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for mode, rows in (("subway", subway_rows), ("bus", bus_rows)):
        for row in rows:
            minute = service_minute(row["time"], mode=mode)
            grouped[row["code"]][(mode, row["day_type"])].append(
                {"time": row["time"], "display_time": display_time(minute), "service_minute": minute, "congestion": as_float(row["congestion"], 1)}
            )
    out: dict[str, dict[str, Any]] = {}
    for code, wrapper in regions.items():
        region = wrapper["region"]
        area = region["area_km2"]
        bus_density = density(bus_counts.get(code, 0), area)
        station_density = density(station_counts.get(code, 0), area)
        bus_delta = pct_delta(bus_density, seoul_bus_density)
        station_delta = pct_delta(station_density, seoul_station_density)
        bus_tone = tone_from_delta(bus_delta, threshold=0.15)
        station_tone = tone_from_delta(station_delta, threshold=0.15)
        if station_tone == "good" and bus_tone == "good":
            headline = "지하철역과 버스정류장 밀도가 모두 높습니다"
        elif station_tone == "bad" and bus_tone == "bad":
            headline = "교통시설 밀도가 서울 기준보다 낮습니다"
        elif bus_tone == "good":
            headline = "버스정류장 밀도가 서울 기준보다 높습니다"
        elif station_tone == "good":
            headline = "지하철역 밀도가 서울 기준보다 높습니다"
        else:
            headline = "지하철과 버스 공급 밀도를 서울 기준으로 봅니다"
        overview = {
            "region": region,
            "headline": headline,
            "summary": (
                f"지하철역 밀도는 서울 평균보다 {'높은 편' if station_tone == 'good' else '낮은 편' if station_tone == 'bad' else '비슷한 편'}입니다. "
                f"버스정류장 밀도는 서울 평균보다 {'높은 편' if bus_tone == 'good' else '낮은 편' if bus_tone == 'bad' else '비슷한 편'}입니다."
            ),
            "quicktakes": [
                quicktake("역 많음" if station_tone == "good" else "역 적음" if station_tone == "bad" else "역 보통", station_tone),
                quicktake("버스 많음" if bus_tone == "good" else "버스 적음" if bus_tone == "bad" else "버스 보통", bus_tone),
            ],
            "station_names": sorted(station_names.get(code, [])),
            "station_items": sorted(
                station_items.get(code, []),
                key=lambda item: (
                    item["distance_m"] if isinstance(item.get("distance_m"), (int, float)) else float("inf"),
                    item["name"],
                ),
            ),
            "metrics": [
                metric("subway_station_density", "지하철역 밀도", round(station_density, 2) if station_density is not None else None, "곳/km²", tone=station_tone, badge="많음" if station_tone == "good" else "적음" if station_tone == "bad" else "보통", description=fmt_delta(station_delta, "서울 평균")),
                metric("bus_stop_density", "버스정류장 밀도", round(bus_density, 2) if bus_density is not None else None, "곳/km²", tone=bus_tone, badge="많음" if bus_tone == "good" else "적음" if bus_tone == "bad" else "보통", description=fmt_delta(bus_delta, "서울 평균")),
            ],
            "basis": {"comparison": "서울 전체 면적당 교통시설 밀도 기준", "route_preview": "disabled", "station_list": f"{nearest_table} 1km boundary cache"},
        }
        lines = []
        for mode, mode_label in (("subway", "지하철"), ("bus", "버스")):
            for day_type in ("평일", "주말"):
                items = sorted(grouped.get(code, {}).get((mode, day_type), []), key=lambda item: item["service_minute"])
                lines.append({
                    "key": f"{mode}_{'weekday' if day_type == '평일' else 'weekend'}",
                    "mode": mode,
                    "day_type": day_type,
                    "label": f"{mode_label} {day_type}",
                    "items": items,
                    "axis": {
                        "start_minute": 330 if mode == "subway" else 240,
                        "end_minute": 1470 if mode == "subway" else 1620,
                        "start_label": "05:30" if mode == "subway" else "04:00",
                        "end_label": "익일 00:30" if mode == "subway" else "익일 03:00",
                    },
                })
        out[code] = {
            "overview": overview,
            "congestion": {
                "region": region,
                "series": lines,
                "subway": next((line["items"] for line in lines if line["key"] == "subway_weekday"), []),
                "bus": next((line["items"] for line in lines if line["key"] == "bus_weekday"), []),
                "basis": {
                    "subway_day_types": ["평일", "토요일", "일요일", "휴일"],
                    "bus_day_types": ["평일", "주말"],
                    "subway_axis": "05:30~익일 00:30",
                    "bus_axis": "04:00~익일 03:00",
                    "subway_method": "1km 이내 역 혼잡도 거리 가중 평균",
                    "subway_weight": "1 / (distance_m + 200)",
                },
            },
        }
    return out


def build_infra_parts(config: RegionConfig, regions: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    codes = list(regions)
    if not codes:
        return {}
    total_area = sum(float(item["region"]["area_km2"] or 0) for item in regions.values()) or 1
    group_by_category = {category: {"key": group["key"], "label": group["label"]} for group in INFRA_GROUPS for category in group["categories"]}
    counts: dict[str, dict[str, int]] = defaultdict(dict)
    category_totals: dict[str, int] = defaultdict(int)
    for row in fetchall(
        f"""
        SELECT l.{config.code_col} AS code, a.category, COUNT(DISTINCT l.amenity_id)::int AS count
        FROM {config.amenity_link_table} l
        JOIN amenity a ON a.id = l.amenity_id
        WHERE l.{config.code_col} = ANY(%s) AND a.category = ANY(%s)
        GROUP BY l.{config.code_col}, a.category
        """,
        [codes, VISUAL_CATEGORIES],
    ):
        counts[row["code"]][row["category"]] = row["count"]
        category_totals[row["category"]] += row["count"]
    seoul_category_density = {category: category_totals.get(category, 0) / total_area for category in VISUAL_CATEGORIES}
    park_area: dict[str, float] = defaultdict(float)
    for row in fetchall(
        f"""
        SELECT l.{config.code_col} AS code,
               SUM(ST_Area(ST_Intersection(p.boundary, r.boundary)::geography))::float AS area_m2
        FROM {config.park_link_table} l
        JOIN park p ON p.id = l.park_id
        JOIN {config.table} r ON r.{config.code_col} = l.{config.code_col}
        WHERE l.{config.code_col} = ANY(%s) AND ST_Intersects(p.boundary, r.boundary)
        GROUP BY l.{config.code_col}
        """,
        [codes],
    ):
        park_area[row["code"]] = as_float(row["area_m2"]) or 0.0
    seoul_green_ratio = (sum(park_area.values()) / (total_area * 1_000_000.0) * 100) if total_area else None
    open_day = DAY_BY_WEEKDAY[timezone.localdate().weekday()]
    open_medical = {row["code"]: row["count"] for row in fetchall(
        f"""
        SELECT f.{config.code_col} AS code, COUNT(DISTINCT f.hpid)::int AS count
        FROM medical_facility f
        JOIN medical_facility_hours h ON h.hpid = f.hpid
        WHERE f.{config.code_col} = ANY(%s) AND h.day_type = %s AND h.is_closed = false
        GROUP BY f.{config.code_col}
        """,
        [codes, open_day],
    )}
    emergency = {row["code"]: row["count"] for row in fetchall(
        f"""
        SELECT f.{config.code_col} AS code, COUNT(DISTINCT e.hpid)::int AS count
        FROM medical_facility f
        JOIN medical_emergency e ON e.hpid = f.hpid
        WHERE f.{config.code_col} = ANY(%s)
        GROUP BY f.{config.code_col}
        """,
        [codes],
    )}
    out: dict[str, dict[str, Any]] = {}
    seoul_total_density = sum(category_totals.values()) / total_area
    seoul_food_density = sum(category_totals.get(category, 0) for category in FOOD_CATEGORIES) / total_area
    seoul_medical_density = sum(category_totals.get(category, 0) for category in MEDICAL_CATEGORIES) / total_area
    seoul_emergency_density = sum(emergency.values()) / total_area
    for code, wrapper in regions.items():
        region = wrapper["region"]
        area = region["area_km2"]
        by_cat = counts.get(code, {})
        total = sum(by_cat.get(category, 0) for category in VISUAL_CATEGORIES)
        food = sum(by_cat.get(category, 0) for category in FOOD_CATEGORIES)
        medical_count = sum(by_cat.get(category, 0) for category in MEDICAL_CATEGORIES)
        total_density = density(total, area)
        food_density = density(food, area)
        medical_density = density(medical_count, area)
        emergency_density = density(emergency.get(code, 0), area)
        green_ratio = (park_area.get(code, 0) / (float(area) * 1_000_000.0) * 100) if area else None
        infra_delta = pct_delta(total_density, seoul_total_density)
        food_delta = pct_delta(food_density, seoul_food_density)
        medical_delta = pct_delta(medical_density, seoul_medical_density)
        emergency_delta = pct_delta(emergency_density, seoul_emergency_density)
        green_delta = pct_delta(green_ratio, seoul_green_ratio)
        infra_tone = tone_from_delta(infra_delta, threshold=0.15)
        medical_tone = tone_from_delta(medical_delta, threshold=0.15)
        emergency_tone = tone_from_delta(emergency_delta, threshold=0.15)
        green_tone = tone_from_delta(green_delta, threshold=0.15)
        food_tone = tone_from_delta(food_delta, threshold=0.15)
        headline = "생활시설이 충분하고 의료 접근성도 양호합니다"
        if infra_tone == "bad":
            headline = "생활시설 밀도가 낮아 주변 확인이 필요합니다"
        elif medical_tone == "bad":
            headline = "의료시설 접근성은 추가 확인이 필요합니다"
        elif emergency_tone == "bad":
            headline = "응급실은 주변 지역까지 함께 봐야 합니다"
        overview = {
            "region": region,
            "headline": headline,
            "summary": (
                f"{region['dong_name']}의 생활시설 밀도는 서울 평균보다 {'높은 편' if infra_tone == 'good' else '낮은 편' if infra_tone == 'bad' else '비슷한 편'}입니다. "
                f"식생활 시설은 {food}곳, 약국·병원·치과는 {medical_count}곳입니다. "
                f"응급실은 {emergency.get(code, 0)}곳이고, 오늘 운영 중인 의료시설은 {open_medical.get(code, 0)}곳입니다."
            ),
            "quicktakes": [
                quicktake("생활시설 많음" if infra_tone == "good" else "생활시설 적음" if infra_tone == "bad" else "생활시설 보통", infra_tone),
                quicktake("의료 접근 양호" if medical_tone != "bad" else "의료 부족", medical_tone),
                quicktake("응급실 있음" if emergency_tone == "good" else "응급실 없음", emergency_tone),
            ],
            "metrics": [
                metric("amenity_density", "면적당 시설", round(total_density, 1) if total_density is not None else None, "곳/km²", tone=infra_tone, badge="많음" if infra_tone == "good" else "적음" if infra_tone == "bad" else "보통", description=fmt_delta(infra_delta)),
                metric("green_ratio", "녹지율", round(green_ratio, 1) if green_ratio is not None else None, "%", tone=green_tone, badge="높음" if green_tone == "good" else "낮음" if green_tone == "bad" else "보통", description=fmt_delta(green_delta)),
                metric("food_density", "식생활 밀도", round(food_density, 1) if food_density is not None else None, "곳/km²", tone=food_tone, badge="많음" if food_tone == "good" else "적음" if food_tone == "bad" else "보통", description=fmt_delta(food_delta)),
                metric("medical_density", "의료 밀도", round(medical_density, 1) if medical_density is not None else None, "곳/km²", tone=medical_tone, badge="많음" if medical_tone == "good" else "적음" if medical_tone == "bad" else "보통", description=f"{fmt_delta(medical_delta)} · 오늘 운영 {open_medical.get(code, 0)}곳"),
            ],
            "basis": {"source": "amenity + medical public_data", "comparison": "서울 전체 면적당 시설 밀도 기준"},
        }
        visual_total = sum(by_cat.get(category, 0) for category in VISUAL_CATEGORIES) or 1
        items = []
        for category in VISUAL_CATEGORIES:
            count = by_cat.get(category, 0)
            item_density = density(count, area) or 0
            seoul_density = seoul_category_density.get(category, 0)
            item_delta = pct_delta(item_density, seoul_density)
            composition_value = item_density
            display_value = f"{count:,}곳"
            display_unit = "곳/km²"
            if category == "park":
                item_density = green_ratio or 0
                seoul_density = seoul_green_ratio or 0
                item_delta = green_delta
                composition_value = item_density
                display_value = f"{item_density:.1f}%"
                display_unit = "녹지율"
            items.append({
                "category": category,
                "label": CATEGORY_LABELS.get(category, category),
                "count": count,
                "ratio": round(count / visual_total * 100, 1),
                "density": round(item_density, 2),
                "seoul_density": round(seoul_density, 2),
                "delta": item_delta,
                "composition_value": round(composition_value, 2),
                "display_value": display_value,
                "display_unit": display_unit,
                "group_key": group_by_category[category]["key"],
                "group_label": group_by_category[category]["label"],
            })
        out[code] = {
            "overview": overview,
            "category_mix": {
                "region": region,
                "items": items,
                "groups": INFRA_GROUPS,
                "basis": {"source": "amenity", "comparison": "서울 전체 면적당 시설 밀도 기준", "park_delta_basis": "공원은 공원 면적 / 지역 면적 기준"},
            },
        }
    return out


def grade_score(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(100.0, (6.0 - value) / 5.0 * 100.0))


def build_safety_parts(config: RegionConfig, regions: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    seoul_score = as_float(fetchone("SELECT score_safety FROM current_seoul LIMIT 1").get("score_safety"), 1)
    gu_codes = sorted({item["region"]["gu_code"] for item in regions.values()})
    metric_codes = [code for code, _label in SAFETY_GRADE_METRICS]
    gu_rows = fetchall(
        """
        SELECT DISTINCT ON (gu_code, metric_code) gu_code, metric_code, value::float AS value, date
        FROM gu_metric
        WHERE gu_code = ANY(%s) AND metric_code = ANY(%s)
        ORDER BY gu_code, metric_code, date DESC
        """,
        [gu_codes, metric_codes],
    )
    seoul_rows = fetchall(
        """
        SELECT DISTINCT ON (metric_code) metric_code, value::float AS value, date
        FROM seoul_metric
        WHERE metric_code = ANY(%s)
        ORDER BY metric_code, date DESC
        """,
        [metric_codes],
    )
    gu_metrics: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in gu_rows:
        gu_metrics[row["gu_code"]][row["metric_code"]] = row
    seoul_metrics = {row["metric_code"]: row for row in seoul_rows}
    out: dict[str, dict[str, Any]] = {}
    for code, wrapper in regions.items():
        region = wrapper["region"]
        score = wrapper["scores"].get("score_safety")
        rank = wrapper["scores"].get("rank_safety")
        delta = pct_delta(score, seoul_score)
        tone = tone_from_delta(delta, threshold=0.08)
        if score is not None and score < 45:
            tone = "bad"
        elif score is not None and score >= 70:
            tone = "good"
        headline = "안전 점수는 주변 레이어를 함께 봅니다"
        if tone == "good":
            headline = "안전 점수가 높은 편입니다"
        elif tone == "bad":
            headline = "안전 점수는 주의해서 봐야 합니다"
        summary = f"{region['dong_name']}의 안전 점수는 {score:.1f}점입니다. " if score is not None else f"{region['dong_name']}의 안전 점수 데이터가 없습니다. "
        if seoul_score is not None:
            summary += f"서울 평균 안전 점수는 {seoul_score:.1f}점입니다. "
        summary += "범죄주의구간 지도 레이어는 위치 판단용 보조 정보로 확인합니다."
        grades = []
        for metric_code, label in SAFETY_GRADE_METRICS:
            raw = as_float(gu_metrics.get(region["gu_code"], {}).get(metric_code, {}).get("value"), 2)
            seoul_raw = as_float(seoul_metrics.get(metric_code, {}).get("value"), 2)
            score_value = grade_score(raw)
            seoul_grade_score = grade_score(seoul_raw)
            grade_delta = pct_delta(score_value, seoul_grade_score)
            grade_tone = tone_from_delta(grade_delta, threshold=0.08)
            grades.append({
                "key": metric_code.lower(),
                "label": label,
                "score": round(score_value, 1) if score_value is not None else None,
                "raw_value": raw,
                "seoul_score": round(seoul_grade_score, 1) if seoul_grade_score is not None else None,
                "seoul_raw_value": seoul_raw,
                "unit": "등급",
                "tone": grade_tone,
                "direction": "lower_is_better",
                "interpretation": "원자료 등급은 낮을수록 안전합니다. 레이더는 1등급=100점, 5등급=20점으로 변환해 표시합니다.",
                "date": gu_metrics.get(region["gu_code"], {}).get(metric_code, {}).get("date").isoformat() if gu_metrics.get(region["gu_code"], {}).get(metric_code, {}).get("date") else None,
            })
        overview = {
            "region": region,
            "headline": headline,
            "summary": summary,
            "quicktakes": [quicktake("안전 높음" if tone == "good" else "안전 낮음" if tone == "bad" else "안전 보통", tone), quicktake("범죄주의구간", "bad")],
            "metrics": [
                metric("safety_score", "지역 안전 점수", score, "점", tone=tone, badge="높음" if tone == "good" else "낮음" if tone == "bad" else "보통", description=f"지역안전등급 평균 환산 점수 · 순위 {rank}위" if rank else "지역안전등급 평균 환산 점수"),
                metric("seoul_safety_score", "서울 평균 안전 점수", seoul_score, "점", tone="info", badge="서울", description="서울 자치구 지역안전등급 환산 점수 평균"),
                metric("crime_zone_layer", "범죄주의구간", "지원", "", tone="bad", badge="지도", description="생활안전지도 범죄주의구간"),
            ],
            "basis": {"score_source": "지역안전등급 평균 환산 점수", "comparison": "서울 평균 안전 점수 기준", "wms_source": "생활안전지도"},
        }
        out[code] = {
            "overview": overview,
            "grades": {"region": region, "items": grades, "basis": {"source": "metric_gu safety grades", "comparison": "서울 안전등급 지표", "score_transform": "1등급=100점, 5등급=20점"}},
            "wms": {
                "key": "crime_zone",
                "name": "범죄주의구간",
                "source": "safemap",
                "int_id": "IF_0087",
                "service_key_exposed": False,
                "params": {"layers": "A2SM_CRMNLHSPOT_TOT", "styles": "A2SM_CrmnlHspot_Tot_Tot", "srs": "EPSG:4326", "format": "image/png", "transparent": True},
                "region": region,
            },
        }
    return out


def build_dashboard_payloads(region_type: str, *, limit: int | None = None, offset: int = 0) -> dict[str, dict[str, Any]]:
    config = CONFIGS[region_type]
    regions = load_regions(config, limit=limit, offset=offset)
    if not regions:
        return {}
    rent_parts = build_rent_parts(config, regions)
    transit_parts = build_transit_parts(config, regions)
    infra_parts = build_infra_parts(config, regions)
    safety_parts = build_safety_parts(config, regions)
    computed_at = timezone.now().isoformat()
    payloads: dict[str, dict[str, Any]] = {}
    for code, wrapper in regions.items():
        region = wrapper["region"]
        intro = build_intro(region)
        payloads[code] = {
            "region": region,
            "intro": intro,
            "rent_summary": rent_parts.get(code, {}),
            "transit_summary": transit_parts.get(code, {}),
            "infra_summary": infra_parts.get(code, {}),
            "safety_summary": safety_parts.get(code, {}),
            "source_version": CACHE_SOURCE_VERSION,
            "computed_at": computed_at,
        }
    return payloads
