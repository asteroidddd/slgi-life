from __future__ import annotations

from typing import Any

from django.db import connection, transaction

from apps.public_data.rent_deal.utils import get_monthly_conversion_rate


INT4_MAX = 2_147_483_647
INT2_MAX = 32_767
TYPE_CODE_BY_HOUSING_TYPE = {
    "아파트": "A",
    "오피스텔": "O",
    "연립": "Y",
    "다세대": "D",
    "연립다세대": "V",
    "다가구": "M",
    "단독": "H",
}


def _fetch_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row, strict=True))


def _fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in rows]


def _source_stats() -> dict[str, Any]:
    monthly_rate = float(get_monthly_conversion_rate())
    return _fetch_one(
        """
        SELECT
            COUNT(*) AS source_count,
            COUNT(location) AS source_location_count,
            MAX(length(id)) AS max_id_length,
            MAX(deposit) AS max_deposit,
            MAX(monthly_rent) AS max_monthly_rent,
            MAX(round(monthly_rent::double precision + deposit::double precision * %s))
                AS max_converted_rent,
            MAX(area_m2) AS max_area_m2,
            MIN(contract_date) AS min_contract_date,
            MAX(contract_date) AS max_contract_date
        FROM rent_deal
        """,
        (monthly_rate,),
    )


def _housing_type_counts() -> dict[str, int]:
    rows = _fetch_all(
        """
        SELECT housing_type, COUNT(*) AS row_count
        FROM rent_deal
        GROUP BY housing_type
        ORDER BY housing_type
        """
    )
    return {row["housing_type"]: row["row_count"] for row in rows}


def _cache_stats() -> dict[str, Any]:
    exists = _fetch_one(
        """
        SELECT to_regclass('public.rent_deal_cache') IS NOT NULL AS exists
        """
    )["exists"]
    if not exists:
        return {
            "cache_exists": False,
            "cache_count": None,
            "cache_location_count": None,
            "cache_size": None,
            "cache_heap_size": None,
            "cache_index_size": None,
        }

    columns = {
        row["column_name"]
        for row in _fetch_all(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'rent_deal_cache'
            """
        )
    }
    if {"lng", "lat"}.issubset(columns):
        location_count_sql = "COUNT(*) FILTER (WHERE lng IS NOT NULL AND lat IS NOT NULL)"
    else:
        location_count_sql = "COUNT(location)"

    stats = _fetch_one(
        f"""
        SELECT
            COUNT(*) AS cache_count,
            {location_count_sql} AS cache_location_count,
            pg_size_pretty(pg_relation_size('rent_deal_cache')) AS cache_heap_size,
            pg_size_pretty(pg_indexes_size('rent_deal_cache')) AS cache_index_size,
            pg_size_pretty(pg_total_relation_size('rent_deal_cache')) AS cache_size
        FROM rent_deal_cache
        """
    )
    stats["cache_exists"] = True
    stats["cache_columns"] = sorted(columns)
    return stats


def _validate_source_ranges(stats: dict[str, Any]) -> None:
    max_id_length = stats.get("max_id_length") or 0
    max_deposit = stats.get("max_deposit") or 0
    max_monthly_rent = stats.get("max_monthly_rent") or 0
    max_converted_rent = stats.get("max_converted_rent") or 0
    if max_id_length > 20:
        raise ValueError(f"rent_deal.id max length {max_id_length} exceeds varchar(20).")
    if max_deposit > INT4_MAX:
        raise ValueError(
            f"rent_deal.deposit max {max_deposit} exceeds IntegerField limit {INT4_MAX}."
        )
    if max_monthly_rent > INT2_MAX:
        raise ValueError(
            f"rent_deal.monthly_rent max {max_monthly_rent} exceeds SmallIntegerField limit {INT2_MAX}."
        )
    if max_converted_rent > INT2_MAX:
        raise ValueError(
            f"converted_rent max {max_converted_rent} exceeds SmallIntegerField limit {INT2_MAX}."
        )


def _validate_housing_types(type_counts: dict[str, int]) -> None:
    unknown = sorted(set(type_counts) - set(TYPE_CODE_BY_HOUSING_TYPE))
    if unknown:
        raise ValueError(f"Unknown rent_deal.housing_type values: {unknown}")


def inspect_rent_deal_cache_source() -> dict[str, Any]:
    """Return source/cache stats without writing to the database."""

    source = _source_stats()
    type_counts = _housing_type_counts()
    _validate_source_ranges(source)
    _validate_housing_types(type_counts)
    cache = _cache_stats()
    return {
        "source_count": source["source_count"],
        "source_location_count": source["source_location_count"],
        "max_id_length": source["max_id_length"],
        "max_deposit": source["max_deposit"],
        "max_monthly_rent": source["max_monthly_rent"],
        "max_converted_rent": int(source["max_converted_rent"] or 0),
        "max_area_m2": float(source["max_area_m2"] or 0.0),
        "min_contract_date": source["min_contract_date"],
        "max_contract_date": source["max_contract_date"],
        "housing_type_counts": type_counts,
        "type_code_mapping": TYPE_CODE_BY_HOUSING_TYPE,
        **cache,
    }


def rebuild_rent_deal_cache(*, dry_run: bool = False) -> dict[str, Any]:
    """Rebuild rent_deal_cache from rent_deal using one SQL bulk insert."""

    source = _source_stats()
    type_counts = _housing_type_counts()
    _validate_source_ranges(source)
    _validate_housing_types(type_counts)

    monthly_rate = float(get_monthly_conversion_rate())
    before_cache = _cache_stats()
    stats: dict[str, Any] = {
        "dry_run": dry_run,
        "monthly_conversion_rate": monthly_rate,
        "source_count": source["source_count"],
        "source_location_count": source["source_location_count"],
        "max_id_length": source["max_id_length"],
        "max_deposit": source["max_deposit"],
        "max_monthly_rent": source["max_monthly_rent"],
        "max_converted_rent": int(source["max_converted_rent"] or 0),
        "max_area_m2": float(source["max_area_m2"] or 0.0),
        "min_contract_date": source["min_contract_date"],
        "max_contract_date": source["max_contract_date"],
        "housing_type_counts": type_counts,
        "type_code_mapping": TYPE_CODE_BY_HOUSING_TYPE,
        "before_cache": before_cache,
    }
    if dry_run:
        return stats

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE rent_deal_cache")
            cursor.execute(
                """
                INSERT INTO rent_deal_cache (
                    id,
                    type_code,
                    deposit,
                    monthly_rent,
                    converted_rent,
                    area_m2,
                    lng,
                    lat,
                    contract_ymd
                )
                SELECT
                    id,
                    CASE housing_type
                        WHEN '아파트' THEN 'A'
                        WHEN '오피스텔' THEN 'O'
                        WHEN '연립' THEN 'Y'
                        WHEN '다세대' THEN 'D'
                        WHEN '연립다세대' THEN 'V'
                        WHEN '다가구' THEN 'M'
                        WHEN '단독' THEN 'H'
                    END,
                    deposit::integer,
                    monthly_rent::smallint,
                    round(
                        monthly_rent::double precision + deposit::double precision * %s
                    )::smallint,
                    area_m2::real,
                    ST_X(location),
                    ST_Y(location),
                    (
                        EXTRACT(YEAR FROM contract_date)::integer * 10000
                        + EXTRACT(MONTH FROM contract_date)::integer * 100
                        + EXTRACT(DAY FROM contract_date)::integer
                    )::integer
                FROM rent_deal
                """,
                [monthly_rate],
            )
            inserted = cursor.rowcount

    after_cache = _cache_stats()
    stats.update(
        {
            "inserted": inserted,
            "after_cache": after_cache,
        }
    )
    return stats
