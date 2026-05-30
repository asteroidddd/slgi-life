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
    adong_count_sql = (
        "COUNT(*) FILTER (WHERE adong_code IS NOT NULL)"
        if "adong_code" in columns
        else "NULL::bigint"
    )
    ldong_count_sql = (
        "COUNT(*) FILTER (WHERE ldong_code IS NOT NULL)"
        if "ldong_code" in columns
        else "NULL::bigint"
    )
    gu_count_sql = (
        "COUNT(*) FILTER (WHERE gu_code IS NOT NULL)"
        if "gu_code" in columns
        else "NULL::bigint"
    )

    stats = _fetch_one(
        f"""
        SELECT
            COUNT(*) AS cache_count,
            {location_count_sql} AS cache_location_count,
            {adong_count_sql} AS cache_adong_count,
            {ldong_count_sql} AS cache_ldong_count,
            {gu_count_sql} AS cache_gu_count,
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


def ensure_rent_deal_cache_table() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE rent_deal_cache
                ADD COLUMN IF NOT EXISTS ldong_code varchar(20) NULL,
                ADD COLUMN IF NOT EXISTS adong_code varchar(20) NULL,
                ADD COLUMN IF NOT EXISTS gu_code varchar(20) NULL;
            CREATE INDEX IF NOT EXISTS rent_deal_cache_match_filter_idx
                ON rent_deal_cache (type_code, contract_ymd, adong_code)
                INCLUDE (area_m2, converted_rent, deposit, monthly_rent)
                WHERE adong_code IS NOT NULL AND area_m2 IS NOT NULL;
            CREATE INDEX IF NOT EXISTS rent_deal_cache_gu_loc_idx
                ON rent_deal_cache (gu_code)
                WHERE gu_code IS NOT NULL AND lng IS NOT NULL AND lat IS NOT NULL;
            """
        )


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
    if not dry_run:
        ensure_rent_deal_cache_table()

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
                    contract_ymd,
                    ldong_code,
                    adong_code,
                    gu_code
                )
                SELECT
                    r.id,
                    CASE r.housing_type
                        WHEN '아파트' THEN 'A'
                        WHEN '오피스텔' THEN 'O'
                        WHEN '연립' THEN 'Y'
                        WHEN '다세대' THEN 'D'
                        WHEN '연립다세대' THEN 'V'
                        WHEN '다가구' THEN 'M'
                        WHEN '단독' THEN 'H'
                    END,
                    r.deposit::integer,
                    r.monthly_rent::smallint,
                    round(
                        r.monthly_rent::double precision + r.deposit::double precision * %s
                    )::smallint,
                    r.area_m2::real,
                    ST_X(r.location),
                    ST_Y(r.location),
                    (
                        EXTRACT(YEAR FROM r.contract_date)::integer * 10000
                        + EXTRACT(MONTH FROM r.contract_date)::integer * 100
                        + EXTRACT(DAY FROM r.contract_date)::integer
                    )::integer,
                    r.ldong_code,
                    r.adong_code,
                    l.gu_code
                FROM rent_deal r
                LEFT JOIN ldong l ON l.ldong_code = r.ldong_code
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



GRID_SIZE_M = 300


def _summary_cache_stats() -> dict[str, Any]:
    rows = _fetch_all(
        """
        SELECT table_name, to_regclass('public.' || table_name) IS NOT NULL AS exists
        FROM (VALUES
            ('rent_deal_ldong_monthly_cache'),
            ('rent_deal_grid_monthly_cache')
        ) AS t(table_name)
        """
    )
    stats: dict[str, Any] = {}
    for row in rows:
        name = row["table_name"]
        if not row["exists"]:
            stats[name] = {"exists": False, "count": None, "size": None}
            continue
        stats[name] = _fetch_one(
            f"""
            SELECT
                TRUE AS exists,
                COUNT(*) AS count,
                pg_size_pretty(pg_total_relation_size('{name}')) AS size
            FROM {name}
            """
        )
    return stats


def ensure_rent_deal_summary_cache_tables() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rent_deal_ldong_monthly_cache (
                cache_key varchar(40) NOT NULL,
                ldong_code varchar(20) NOT NULL,
                ldong_name varchar(100) NOT NULL,
                gu_code varchar(20) NOT NULL,
                gu_name varchar(100) NOT NULL,
                year_month integer NOT NULL,
                type_code char(1) NOT NULL,
                avg_converted_rent smallint NOT NULL,
                deal_count integer NOT NULL,
                center_lng double precision NULL,
                center_lat double precision NULL
            );
            CREATE TABLE IF NOT EXISTS rent_deal_grid_monthly_cache (
                cache_key varchar(48) NOT NULL,
                grid_id varchar(32) NOT NULL,
                grid_size_m smallint NOT NULL DEFAULT 300,
                gu_code varchar(20) NOT NULL,
                gu_name varchar(100) NOT NULL,
                year_month integer NOT NULL,
                type_code char(1) NOT NULL,
                avg_converted_rent smallint NOT NULL,
                deal_count integer NOT NULL,
                center_lng double precision NULL,
                center_lat double precision NULL
            );
            CREATE INDEX IF NOT EXISTS rent_ldong_month_type_idx
                ON rent_deal_ldong_monthly_cache (year_month, type_code);
            CREATE INDEX IF NOT EXISTS rent_ldong_code_idx
                ON rent_deal_ldong_monthly_cache (ldong_code);
            CREATE INDEX IF NOT EXISTS rent_grid_month_type_idx
                ON rent_deal_grid_monthly_cache (year_month, type_code);
            CREATE INDEX IF NOT EXISTS rent_grid_gu_idx
                ON rent_deal_grid_monthly_cache (gu_code);
            CREATE INDEX IF NOT EXISTS rent_grid_center_idx
                ON rent_deal_grid_monthly_cache (center_lng, center_lat);
            CREATE INDEX IF NOT EXISTS rent_ldong_type_month_code_idx
                ON rent_deal_ldong_monthly_cache (type_code, year_month, ldong_code);
            CREATE INDEX IF NOT EXISTS rent_grid_type_month_center_idx
                ON rent_deal_grid_monthly_cache (type_code, year_month, center_lng, center_lat);
            """
        )


def inspect_rent_deal_summary_cache_source() -> dict[str, Any]:
    return {
        "grid_size_m": GRID_SIZE_M,
        "rent_deal_cache": _cache_stats(),
        "summary_caches": _summary_cache_stats(),
    }


def rebuild_rent_deal_summary_caches(*, dry_run: bool = False) -> dict[str, Any]:
    """Rebuild low/mid zoom rent summary caches from rent_deal_cache."""

    ensure_rent_deal_summary_cache_tables()
    before = _summary_cache_stats()
    stats: dict[str, Any] = {
        "dry_run": dry_run,
        "grid_size_m": GRID_SIZE_M,
        "before_summary_caches": before,
    }
    if dry_run:
        return stats

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE rent_deal_ldong_monthly_cache")
            cursor.execute(
                """
                INSERT INTO rent_deal_ldong_monthly_cache (
                    cache_key,
                    ldong_code,
                    ldong_name,
                    gu_code,
                    gu_name,
                    year_month,
                    type_code,
                    avg_converted_rent,
                    deal_count,
                    center_lng,
                    center_lat
                )
                SELECT
                    c.ldong_code || ':' || (c.contract_ymd / 100)::integer::text || ':' || c.type_code,
                    c.ldong_code,
                    l.name,
                    g.gu_code,
                    g.name,
                    (c.contract_ymd / 100)::integer AS year_month,
                    c.type_code,
                    ROUND(AVG(c.converted_rent))::smallint AS avg_converted_rent,
                    COUNT(*)::integer AS deal_count,
                    COALESCE(ST_X(l.location), AVG(c.lng)) AS center_lng,
                    COALESCE(ST_Y(l.location), AVG(c.lat)) AS center_lat
                FROM rent_deal_cache c
                JOIN ldong l ON l.ldong_code = c.ldong_code
                JOIN gu g ON g.gu_code = l.gu_code
                WHERE c.lng IS NOT NULL
                  AND c.lat IS NOT NULL
                  AND c.ldong_code IS NOT NULL
                GROUP BY c.ldong_code, l.name, g.gu_code, g.name, year_month, c.type_code, l.location
                """
            )
            ldong_inserted = cursor.rowcount

            cursor.execute("TRUNCATE TABLE rent_deal_grid_monthly_cache")
            cursor.execute(
                """
                WITH source AS (
                    SELECT
                        c.gu_code,
                        g.name AS gu_name,
                        (c.contract_ymd / 100)::integer AS year_month,
                        c.type_code,
                        c.converted_rent,
                        FLOOR(ST_X(ST_Transform(ST_SetSRID(ST_MakePoint(c.lng, c.lat), 4326), 5179)) / %s)::integer AS gx,
                        FLOOR(ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint(c.lng, c.lat), 4326), 5179)) / %s)::integer AS gy
                    FROM rent_deal_cache c
                    JOIN gu g ON g.gu_code = c.gu_code
                    WHERE c.lng IS NOT NULL
                      AND c.lat IS NOT NULL
                      AND c.gu_code IS NOT NULL
                ), grouped AS (
                    SELECT
                        gu_code,
                        gu_name,
                        year_month,
                        type_code,
                        gx,
                        gy,
                        ROUND(AVG(converted_rent))::smallint AS avg_converted_rent,
                        COUNT(*)::integer AS deal_count
                    FROM source
                    GROUP BY gu_code, gu_name, year_month, type_code, gx, gy
                )
                INSERT INTO rent_deal_grid_monthly_cache (
                    cache_key,
                    grid_id,
                    grid_size_m,
                    gu_code,
                    gu_name,
                    year_month,
                    type_code,
                    avg_converted_rent,
                    deal_count,
                    center_lng,
                    center_lat
                )
                SELECT
                    gx::text || ':' || gy::text || ':' || year_month::text || ':' || type_code,
                    gx::text || ':' || gy::text,
                    %s,
                    gu_code,
                    gu_name,
                    year_month,
                    type_code,
                    avg_converted_rent,
                    deal_count,
                    ST_X(ST_Transform(ST_SetSRID(ST_MakePoint((gx + 0.5) * %s, (gy + 0.5) * %s), 5179), 4326)),
                    ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint((gx + 0.5) * %s, (gy + 0.5) * %s), 5179), 4326))
                FROM grouped
                """,
                [GRID_SIZE_M, GRID_SIZE_M, GRID_SIZE_M, GRID_SIZE_M, GRID_SIZE_M, GRID_SIZE_M, GRID_SIZE_M],
            )
            grid_inserted = cursor.rowcount

    after = _summary_cache_stats()
    stats.update(
        {
            "ldong_inserted": ldong_inserted,
            "grid_inserted": grid_inserted,
            "after_summary_caches": after,
        }
    )
    return stats
