"""Recompute current_* score cache tables."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

from django.db import connection, transaction
from django.db.models import Count, Min
from django.utils import timezone

from apps.public_data.bus.models import BusStop
from apps.public_data.metrics.models import GuMetric
from apps.public_data.regions.models import Adong, Gu, Ldong, Seoul
from apps.public_data.rent_deal.utils import get_monthly_conversion_rate
from apps.public_data.subway.models import NearestSubwayAdong, NearestSubwayLdong
from apps.service.amenities.models import Amenity, AmenityAdong, AmenityLdong
from apps.service.heatmap.models import CurrentAdong, CurrentGu, CurrentLdong, CurrentSeoul


RENT_LOOKBACK_DAYS = 365
RENT_TRIM_RATIO = 0.05
RENT_MIN_DEALS = 3
SUBWAY_WEIGHT = 0.60
BUS_WEIGHT = 0.40
SUBWAY_DISTANCE_CAP_M = 1000.0
AMENITY_LIFE_WEIGHT = 0.609
AMENITY_MEDICAL_WEIGHT = 0.108
AMENITY_PARK_WEIGHT = 0.283

LIFE_CATEGORIES = {
    "convenience",
    "mart",
    "daiso",
    "restaurant",
    "cafe",
    "nightlife",
    "laundry",
    "beauty",
    "oliveyoung",
    "gym",
    "book_stationery",
    "study_cafe",
    "etc",
    "library",
}
MEDICAL_CATEGORIES = {"hospital", "dental", "pharmacy"}


@dataclass(frozen=True)
class Unit:
    code: str
    area_km2: float
    parent_code: str | None = None


@dataclass(frozen=True)
class ScoreRow:
    code: str
    score_rent: float | None
    score_amenity: float
    score_transit: float
    score_safety: float
    score_total: float
    rank_rent: int | None = None
    rank_amenity: int | None = None
    rank_transit: int | None = None
    rank_safety: int | None = None
    rank_total: int | None = None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _continuous_percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * pct
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _trimmed_mean(values: list[float]) -> float | None:
    if len(values) < RENT_MIN_DEALS:
        return None
    ordered = sorted(values)
    trim = int(len(ordered) * RENT_TRIM_RATIO)
    trimmed = ordered[trim : len(ordered) - trim] if trim else ordered
    if not trimmed:
        return None
    return statistics.fmean(trimmed)


def _area_km2(area_m2: Any) -> float:
    value = float(area_m2 or 0.0)
    return value / 1_000_000.0 if value > 0 else 0.0


def _score_lower_is_better(raw_by_code: dict[str, float | None]) -> dict[str, float | None]:
    values = [value for value in raw_by_code.values() if value is not None]
    if len(values) < 2:
        return {code: None for code in raw_by_code}
    minimum = min(values)
    p95 = _continuous_percentile(values, 0.95)
    if p95 <= minimum:
        return {code: None for code in raw_by_code}
    return {
        code: None if value is None else _clamp((p95 - value) / (p95 - minimum) * 100.0)
        for code, value in raw_by_code.items()
    }


def _normalize_log_density(raw_density_by_code: dict[str, float]) -> dict[str, float]:
    logs = [math.log1p(max(0.0, value)) for value in raw_density_by_code.values()]
    p95 = _continuous_percentile(logs, 0.95)
    if p95 <= 0:
        return {code: 0.0 for code in raw_density_by_code}
    return {
        code: _clamp(math.log1p(max(0.0, density)) / p95 * 100.0)
        for code, density in raw_density_by_code.items()
    }


def _units() -> tuple[dict[str, Unit], dict[str, Unit], dict[str, Unit], dict[str, Unit]]:
    seouls = {
        row.code: Unit(row.code, _area_km2(row.area_m2))
        for row in Seoul.objects.all()
    }
    gus = {
        row.gu_code: Unit(row.gu_code, _area_km2(row.area_m2))
        for row in Gu.objects.all()
    }
    ldongs = {
        row.ldong_code: Unit(row.ldong_code, _area_km2(row.area_m2), row.gu_id)
        for row in Ldong.objects.select_related("gu")
    }
    adongs = {
        row.adong_code: Unit(row.adong_code, _area_km2(row.area_m2), row.gu_id)
        for row in Adong.objects.select_related("gu")
    }
    return seouls, gus, ldongs, adongs


def _rent_raw_scores(
    seouls: dict[str, Unit],
    gus: dict[str, Unit],
    ldongs: dict[str, Unit],
    adongs: dict[str, Unit],
    *,
    today: date,
) -> tuple[dict[str, float | None], dict[str, float | None], dict[str, float | None], dict[str, float | None]]:
    since = today - timedelta(days=RENT_LOOKBACK_DAYS)
    raw_values: dict[str, dict[str, float]] = {
        "seoul": {},
        "gu": {},
        "ldong": {},
        "adong": {},
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH base AS (
                SELECT
                    (
                        r.monthly_rent::double precision
                        + r.deposit::double precision * %s
                    ) / NULLIF(r.area_m2::double precision, 0) AS value,
                    r.ldong_code,
                    l.gu_code AS ldong_gu_code,
                    r.adong_code,
                    a.gu_code AS adong_gu_code
                FROM rent_deal r
                LEFT JOIN ldong l ON l.ldong_code = r.ldong_code
                LEFT JOIN adong a ON a.adong_code = r.adong_code
                WHERE r.contract_date >= %s
                  AND r.area_m2 IS NOT NULL
                  AND r.area_m2 > 0
            ), scoped AS (
                SELECT 'seoul' AS scope, seoul.code, base.value
                FROM base
                CROSS JOIN unnest(%s::varchar[]) AS seoul(code)
                UNION ALL
                SELECT 'gu', COALESCE(ldong_gu_code, adong_gu_code), value
                FROM base
                WHERE COALESCE(ldong_gu_code, adong_gu_code) IS NOT NULL
                UNION ALL
                SELECT 'ldong', ldong_code, value
                FROM base
                WHERE ldong_code IS NOT NULL
                UNION ALL
                SELECT 'adong', adong_code, value
                FROM base
                WHERE adong_code IS NOT NULL
            ), ranked AS (
                SELECT
                    scope,
                    code,
                    value,
                    COUNT(*) OVER (PARTITION BY scope, code) AS n,
                    ROW_NUMBER() OVER (PARTITION BY scope, code ORDER BY value) AS rn
                FROM scoped
                WHERE value IS NOT NULL
            ), trimmed AS (
                SELECT scope, code, value
                FROM ranked
                WHERE n >= %s
                  AND rn > FLOOR(n * %s)
                  AND rn <= n - FLOOR(n * %s)
            )
            SELECT scope, code, AVG(value)::float AS trimmed_mean
            FROM trimmed
            GROUP BY scope, code
            """,
            [
                get_monthly_conversion_rate(),
                since,
                list(seouls),
                RENT_MIN_DEALS,
                RENT_TRIM_RATIO,
                RENT_TRIM_RATIO,
            ],
        )
        for scope, code, value in cursor.fetchall():
            raw_values[scope][code] = float(value)

    return (
        _score_lower_is_better({code: raw_values["seoul"].get(code) for code in seouls}),
        _score_lower_is_better({code: raw_values["gu"].get(code) for code in gus}),
        _score_lower_is_better({code: raw_values["ldong"].get(code) for code in ldongs}),
        _score_lower_is_better({code: raw_values["adong"].get(code) for code in adongs}),
    )


def _amenity_count_scores(
    units: dict[str, Unit],
    life_counts: dict[str, int],
    medical_counts: dict[str, int],
    park_area_by_code: dict[str, float],
) -> dict[str, float]:
    life_density = {
        code: life_counts.get(code, 0) / unit.area_km2 if unit.area_km2 > 0 else 0.0
        for code, unit in units.items()
    }
    medical_density = {
        code: medical_counts.get(code, 0) / unit.area_km2 if unit.area_km2 > 0 else 0.0
        for code, unit in units.items()
    }
    life = _normalize_log_density(life_density)
    medical = _normalize_log_density(medical_density)
    result: dict[str, float] = {}
    for code, unit in units.items():
        park_ratio_score = 0.0
        if unit.area_km2 > 0:
            park_ratio_score = _clamp((park_area_by_code.get(code, 0.0) / (unit.area_km2 * 1_000_000.0)) * 100.0)
        result[code] = _clamp(
            life[code] * AMENITY_LIFE_WEIGHT
            + medical[code] * AMENITY_MEDICAL_WEIGHT
            + park_ratio_score * AMENITY_PARK_WEIGHT
        )
    return result


def _park_intersection_area_by_region(
    *,
    region_table: str,
    region_pk: str,
    map_table: str | None = None,
    map_region_fk: str | None = None,
) -> dict[str, float]:
    if map_table and map_region_fk:
        sql = f"""
            SELECT
                r.{region_pk},
                COALESCE(
                    SUM(
                        ST_Area(
                            ST_Intersection(
                                ST_MakeValid(r.boundary),
                                ST_MakeValid(p.boundary)
                            )::geography
                        )
                    ),
                    0
                ) AS area_m2
            FROM {map_table} m
            JOIN {region_table} r ON r.{region_pk} = m.{map_region_fk}
            JOIN park p ON p.id = m.park_id
            WHERE r.boundary IS NOT NULL
              AND p.boundary IS NOT NULL
              AND ST_Intersects(r.boundary, p.boundary)
            GROUP BY r.{region_pk}
        """
    else:
        sql = f"""
            SELECT
                r.{region_pk},
                COALESCE(
                    SUM(
                        ST_Area(
                            ST_Intersection(
                                ST_MakeValid(r.boundary),
                                ST_MakeValid(p.boundary)
                            )::geography
                        )
                    ),
                    0
                ) AS area_m2
            FROM {region_table} r
            JOIN park p
              ON r.boundary IS NOT NULL
             AND p.boundary IS NOT NULL
             AND ST_Intersects(r.boundary, p.boundary)
            GROUP BY r.{region_pk}
        """

    with connection.cursor() as cur:
        cur.execute(sql)
        return {str(code): float(area_m2 or 0.0) for code, area_m2 in cur.fetchall()}


def _amenity_scores(
    seouls: dict[str, Unit],
    gus: dict[str, Unit],
    ldongs: dict[str, Unit],
    adongs: dict[str, Unit],
) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    life_all = set(LIFE_CATEGORIES)
    medical_all = set(MEDICAL_CATEGORIES)

    seoul_life = {
        code: Amenity.objects.filter(category__in=life_all).count() for code in seouls
    }
    seoul_medical = {
        code: Amenity.objects.filter(category__in=medical_all).count() for code in seouls
    }
    seoul_park_area = _park_intersection_area_by_region(
        region_table="seoul",
        region_pk="code",
    )

    gu_life: dict[str, int] = defaultdict(int)
    gu_medical: dict[str, int] = defaultdict(int)
    for row in (
        AmenityAdong.objects.values("adong__gu_id", "amenity__category")
        .annotate(n=Count("amenity_id", distinct=True))
    ):
        gu_code = row["adong__gu_id"]
        if row["amenity__category"] in life_all:
            gu_life[gu_code] += row["n"]
        elif row["amenity__category"] in medical_all:
            gu_medical[gu_code] += row["n"]

    gu_park_area = _park_intersection_area_by_region(
        region_table="gu",
        region_pk="gu_code",
    )

    ldong_life: dict[str, int] = defaultdict(int)
    ldong_medical: dict[str, int] = defaultdict(int)
    for row in (
        AmenityLdong.objects.values("ldong_id", "amenity__category")
        .annotate(n=Count("amenity_id", distinct=True))
    ):
        if row["amenity__category"] in life_all:
            ldong_life[row["ldong_id"]] += row["n"]
        elif row["amenity__category"] in medical_all:
            ldong_medical[row["ldong_id"]] += row["n"]

    ldong_park_area = _park_intersection_area_by_region(
        region_table="ldong",
        region_pk="ldong_code",
        map_table="park_ldong",
        map_region_fk="ldong_code",
    )

    adong_life: dict[str, int] = defaultdict(int)
    adong_medical: dict[str, int] = defaultdict(int)
    for row in (
        AmenityAdong.objects.values("adong_id", "amenity__category")
        .annotate(n=Count("amenity_id", distinct=True))
    ):
        if row["amenity__category"] in life_all:
            adong_life[row["adong_id"]] += row["n"]
        elif row["amenity__category"] in medical_all:
            adong_medical[row["adong_id"]] += row["n"]

    adong_park_area = _park_intersection_area_by_region(
        region_table="adong",
        region_pk="adong_code",
        map_table="park_adong",
        map_region_fk="adong_code",
    )

    return (
        _amenity_count_scores(seouls, seoul_life, seoul_medical, seoul_park_area),
        _amenity_count_scores(gus, gu_life, gu_medical, gu_park_area),
        _amenity_count_scores(ldongs, ldong_life, ldong_medical, ldong_park_area),
        _amenity_count_scores(adongs, adong_life, adong_medical, adong_park_area),
    )


def _transit_scores_for_units(
    units: dict[str, Unit],
    nearest_distance_by_code: dict[str, float],
    bus_count_by_code: dict[str, int],
) -> dict[str, float]:
    bus_density = {
        code: bus_count_by_code.get(code, 0) / unit.area_km2 if unit.area_km2 > 0 else 0.0
        for code, unit in units.items()
    }
    bus_signal = _normalize_log_density(bus_density)
    scores = {}
    for code in units:
        distance_m = nearest_distance_by_code.get(code, SUBWAY_DISTANCE_CAP_M)
        subway_signal = max(0.0, 1.0 - min(distance_m, SUBWAY_DISTANCE_CAP_M) / SUBWAY_DISTANCE_CAP_M) * 100.0
        scores[code] = _clamp(subway_signal * SUBWAY_WEIGHT + bus_signal[code] * BUS_WEIGHT)
    return scores


def _transit_scores(
    seouls: dict[str, Unit],
    gus: dict[str, Unit],
    ldongs: dict[str, Unit],
    adongs: dict[str, Unit],
) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    nearest_adong = {
        row["adong_id"]: row["distance_m"]
        for row in NearestSubwayAdong.objects.values("adong_id").annotate(distance_m=Min("distance_m"))
    }
    nearest_ldong = {
        row["ldong_id"]: row["distance_m"]
        for row in NearestSubwayLdong.objects.values("ldong_id").annotate(distance_m=Min("distance_m"))
    }

    adong_bus = {
        row["adong_id"]: row["n"]
        for row in BusStop.objects.filter(adong__isnull=False).values("adong_id").annotate(n=Count("id"))
    }
    ldong_bus = {
        row["ldong_id"]: row["n"]
        for row in BusStop.objects.filter(ldong__isnull=False).values("ldong_id").annotate(n=Count("id"))
    }
    gu_bus: dict[str, int] = defaultdict(int)
    for row in (
        BusStop.objects.filter(adong__isnull=False)
        .values("adong__gu_id")
        .annotate(n=Count("id"))
    ):
        gu_bus[row["adong__gu_id"]] += row["n"]
    seoul_bus = {code: BusStop.objects.count() for code in seouls}

    adong_scores = _transit_scores_for_units(adongs, nearest_adong, adong_bus)
    ldong_scores = _transit_scores_for_units(ldongs, nearest_ldong, ldong_bus)

    gu_scores: dict[str, float] = {}
    for gu_code in gus:
        child_scores = [
            score for code, score in adong_scores.items() if adongs[code].parent_code == gu_code
        ]
        if child_scores:
            gu_scores[gu_code] = statistics.fmean(child_scores)
        else:
            gu_scores[gu_code] = _transit_scores_for_units(
                {gu_code: gus[gu_code]},
                {},
                {gu_code: gu_bus.get(gu_code, 0)},
            )[gu_code]

    seoul_scores = {
        code: statistics.fmean(gu_scores.values()) if gu_scores else _transit_scores_for_units(
            {code: seouls[code]}, {}, {code: seoul_bus.get(code, 0)}
        )[code]
        for code in seouls
    }
    return seoul_scores, gu_scores, ldong_scores, adong_scores


def _rows(
    units: dict[str, Unit],
    rent: dict[str, float | None],
    amenity: dict[str, float],
    transit: dict[str, float],
    safety: dict[str, float],
) -> list[ScoreRow]:
    rows = [
        ScoreRow(
            code=code,
            score_rent=None if rent.get(code) is None else round(float(rent[code]), 1),
            score_amenity=round(amenity.get(code, 0.0), 1),
            score_transit=round(transit.get(code, 0.0), 1),
            score_safety=round(safety.get(code, 0.0), 1),
            score_total=round(
                (((float(rent[code]) if rent.get(code) is not None else 0.0)
                  + amenity.get(code, 0.0)
                  + transit.get(code, 0.0)
                  + safety.get(code, 0.0)) / 4.0),
                1,
            ),
        )
        for code in units
    ]
    _assign_ranks(rows)
    return rows


def _assign_ranks(rows: list[ScoreRow]) -> None:
    for score_attr, rank_attr, include_nulls in (
        ("score_rent", "rank_rent", False),
        ("score_amenity", "rank_amenity", True),
        ("score_transit", "rank_transit", True),
        ("score_safety", "rank_safety", True),
        ("score_total", "rank_total", True),
    ):
        ranked = [
            row for row in rows
            if include_nulls or getattr(row, score_attr) is not None
        ]
        ranked.sort(key=lambda row: float(getattr(row, score_attr) or 0.0), reverse=True)
        current_rank = 0
        last_value = None
        for index, row in enumerate(ranked, start=1):
            value = getattr(row, score_attr)
            if value != last_value:
                current_rank = index
                last_value = value
            object.__setattr__(row, rank_attr, current_rank)


def _safety_scores(
    seouls: dict[str, Unit],
    gus: dict[str, Unit],
    ldongs: dict[str, Unit],
    adongs: dict[str, Unit],
) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    raw_by_gu: dict[str, float] = {}
    for row in (
        GuMetric.objects.filter(metric_id="SAFETY_GRADE_MEAN")
        .order_by("gu_id", "-date")
        .distinct("gu_id")
        .values("gu_id", "value")
    ):
        raw_by_gu[row["gu_id"]] = float(row["value"])

    values = list(raw_by_gu.values())
    if values:
        min_grade = min(values)
        max_grade = max(values)
    else:
        min_grade = max_grade = 0.0

    def convert(gu_code: str | None) -> float:
        if not gu_code or gu_code not in raw_by_gu:
            return 0.0
        grade = raw_by_gu[gu_code]
        if max_grade <= min_grade:
            return 100.0
        return _clamp((max_grade - grade) / (max_grade - min_grade) * 100.0)

    gu_scores = {code: convert(code) for code in gus}
    ldong_scores = {code: convert(unit.parent_code) for code, unit in ldongs.items()}
    adong_scores = {code: convert(unit.parent_code) for code, unit in adongs.items()}
    seoul_value = statistics.fmean(gu_scores.values()) if gu_scores else 0.0
    seoul_scores = {code: seoul_value for code in seouls}
    return seoul_scores, gu_scores, ldong_scores, adong_scores


def _write_current(rows: Iterable[ScoreRow], model: type, fk_name: str) -> int:
    now = timezone.now()
    objects = []
    update_fields = [
        "score_rent",
        "score_amenity",
        "score_transit",
        "score_safety",
        "score_total",
        "updated_at",
    ]
    for row in rows:
        values = {
            "score_rent": row.score_rent,
            "score_amenity": row.score_amenity,
            "score_transit": row.score_transit,
            "score_safety": row.score_safety,
            "score_total": row.score_total,
            "updated_at": now,
        }
        if fk_name != "seoul":
            values |= {
                "rank_rent": row.rank_rent,
                "rank_amenity": row.rank_amenity,
                "rank_transit": row.rank_transit,
                "rank_safety": row.rank_safety,
                "rank_total": row.rank_total,
            }
        objects.append(model(**{f"{fk_name}_id": row.code}, **values))
    if fk_name != "seoul":
        update_fields += [
            "rank_rent",
            "rank_amenity",
            "rank_transit",
            "rank_safety",
            "rank_total",
        ]
    model.objects.bulk_create(
        objects,
        batch_size=1000,
        update_conflicts=True,
        update_fields=update_fields,
        unique_fields=[fk_name],
    )
    return len(objects)


def recompute_current_scores(*, dry_run: bool = False, today: date | None = None) -> dict[str, Any]:
    """Recompute current_seoul/current_gu/current_ldong/current_adong."""

    today = today or date.today()
    seouls, gus, ldongs, adongs = _units()
    rent_seoul, rent_gu, rent_ldong, rent_adong = _rent_raw_scores(
        seouls, gus, ldongs, adongs, today=today
    )
    amenity_seoul, amenity_gu, amenity_ldong, amenity_adong = _amenity_scores(
        seouls, gus, ldongs, adongs
    )
    transit_seoul, transit_gu, transit_ldong, transit_adong = _transit_scores(
        seouls, gus, ldongs, adongs
    )
    safety_seoul, safety_gu, safety_ldong, safety_adong = _safety_scores(
        seouls, gus, ldongs, adongs
    )

    current_rows = {
        "seoul": _rows(seouls, rent_seoul, amenity_seoul, transit_seoul, safety_seoul),
        "gu": _rows(gus, rent_gu, amenity_gu, transit_gu, safety_gu),
        "ldong": _rows(ldongs, rent_ldong, amenity_ldong, transit_ldong, safety_ldong),
        "adong": _rows(adongs, rent_adong, amenity_adong, transit_adong, safety_adong),
    }
    stats = {
        "dry_run": dry_run,
        "today": today.isoformat(),
        "rows": {key: len(value) for key, value in current_rows.items()},
        "rent_nulls": {
            key: sum(1 for row in value if row.score_rent is None)
            for key, value in current_rows.items()
        },
    }
    if dry_run:
        return stats

    with transaction.atomic():
        stats["written"] = {
            "seoul": _write_current(current_rows["seoul"], CurrentSeoul, "seoul"),
            "gu": _write_current(current_rows["gu"], CurrentGu, "gu"),
            "ldong": _write_current(current_rows["ldong"], CurrentLdong, "ldong"),
            "adong": _write_current(current_rows["adong"], CurrentAdong, "adong"),
        }
    return stats
