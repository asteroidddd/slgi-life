"""Recompute current_* score cache tables."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

from django.db import connection, transaction
from django.db.models import Count

from apps.public_data.bus.models import BusStop
from apps.public_data.regions.models import Adong, Gu, Ldong, Seoul
from apps.public_data.rent_deal.models import RentDeal
from apps.public_data.subway.models import NearestSubwayAdong, NearestSubwayLdong
from apps.service.amenities.models import Amenity, AmenityAdong, AmenityLdong
from apps.service.scoring.models import CurrentAdong, CurrentGu, CurrentLdong, CurrentSeoul


RENT_LOOKBACK_DAYS = 365
RENT_CONVERSION_RATE = 0.005
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
    "restaurant",
    "cafe",
    "studycafe",
    "laundry",
    "oliveyoung",
    "gym",
    "etc",
    "library",
    "university",
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
    values = {
        "seoul": defaultdict(list),
        "gu": defaultdict(list),
        "ldong": defaultdict(list),
        "adong": defaultdict(list),
    }

    qs = (
        RentDeal.objects.filter(contract_date__gte=since, area_m2__isnull=False)
        .exclude(area_m2=0)
        .select_related("ldong__gu", "adong__gu")
        .values_list("monthly_rent", "deposit", "area_m2", "ldong_id", "ldong__gu_id", "adong_id", "adong__gu_id")
        .iterator(chunk_size=10000)
    )
    for monthly_rent, deposit, area_m2, ldong_id, ldong_gu_id, adong_id, adong_gu_id in qs:
        area = float(area_m2 or 0.0)
        if area <= 0:
            continue
        value = (float(monthly_rent) + float(deposit) * RENT_CONVERSION_RATE) / area
        for seoul_code in seouls:
            values["seoul"][seoul_code].append(value)
        if ldong_gu_id:
            values["gu"][ldong_gu_id].append(value)
        elif adong_gu_id:
            values["gu"][adong_gu_id].append(value)
        if ldong_id:
            values["ldong"][ldong_id].append(value)
        if adong_id:
            values["adong"][adong_id].append(value)

    return (
        _score_lower_is_better({code: _trimmed_mean(values["seoul"].get(code, [])) for code in seouls}),
        _score_lower_is_better({code: _trimmed_mean(values["gu"].get(code, [])) for code in gus}),
        _score_lower_is_better({code: _trimmed_mean(values["ldong"].get(code, [])) for code in ldongs}),
        _score_lower_is_better({code: _trimmed_mean(values["adong"].get(code, [])) for code in adongs}),
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
        adong_id: distance
        for adong_id, distance in NearestSubwayAdong.objects.filter(rank=1).values_list(
            "adong_id", "distance_m"
        )
    }
    nearest_ldong = {
        ldong_id: distance
        for ldong_id, distance in NearestSubwayLdong.objects.filter(rank=1).values_list(
            "ldong_id", "distance_m"
        )
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
) -> list[ScoreRow]:
    return [
        ScoreRow(
            code=code,
            score_rent=None if rent.get(code) is None else round(float(rent[code]), 1),
            score_amenity=round(amenity.get(code, 0.0), 1),
            score_transit=round(transit.get(code, 0.0), 1),
        )
        for code in units
    ]


def _write_current(rows: Iterable[ScoreRow], model: type, fk_name: str) -> int:
    count = 0
    for row in rows:
        model.objects.update_or_create(
            **{f"{fk_name}_id": row.code},
            defaults={
                "score_rent": row.score_rent,
                "score_amenity": row.score_amenity,
                "score_transit": row.score_transit,
            },
        )
        count += 1
    return count


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

    current_rows = {
        "seoul": _rows(seouls, rent_seoul, amenity_seoul, transit_seoul),
        "gu": _rows(gus, rent_gu, amenity_gu, transit_gu),
        "ldong": _rows(ldongs, rent_ldong, amenity_ldong, transit_ldong),
        "adong": _rows(adongs, rent_adong, amenity_adong, transit_adong),
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
