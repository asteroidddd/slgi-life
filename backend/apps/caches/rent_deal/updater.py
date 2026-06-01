from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from django.db import connection, transaction
from django.utils import timezone

from apps.caches.rent_deal.models import RentDealGeocodeCache


BATCH_SIZE = 5000
SOURCE_VERSION = "rent-deal-geocode-cache-v1"


@dataclass(frozen=True)
class GeocodeCacheRow:
    normalized_query: str
    gu_code: str | None
    ldong_code: str | None
    jibun: str | None
    hit_count: int
    lng: float | None
    lat: float | None
    adong_code: str | None


def _cache_key(normalized_query: str) -> str:
    return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()


def _fetch_source_rows(limit: int | None = None) -> list[GeocodeCacheRow]:
    limit_sql = ""
    params: list[Any] = []
    if limit is not None:
        limit_sql = "LIMIT %s"
        params.append(limit)

    sql = f"""
        WITH rent_rows AS (
            SELECT
                ('서울특별시 ' || g.name || ' ' || l.name || ' ' || trim(r.jibun)) AS normalized_query,
                l.gu_code,
                r.ldong_code,
                trim(r.jibun) AS jibun,
                ST_X(r.location) AS lng,
                ST_Y(r.location) AS lat,
                r.adong_code,
                r.contract_date,
                r.id
            FROM rent_deal r
            JOIN ldong l ON l.ldong_code = r.ldong_code
            JOIN gu g ON g.gu_code = l.gu_code
            WHERE r.jibun IS NOT NULL
              AND trim(r.jibun) <> ''
        ),
        ranked AS (
            SELECT
                *,
                COUNT(*) OVER (PARTITION BY normalized_query) AS hit_count,
                ROW_NUMBER() OVER (
                    PARTITION BY normalized_query
                    ORDER BY
                        CASE WHEN lng IS NULL OR lat IS NULL THEN 1 ELSE 0 END,
                        contract_date DESC NULLS LAST,
                        id DESC
                ) AS rn
            FROM rent_rows
        )
        SELECT
            normalized_query,
            gu_code,
            ldong_code,
            jibun,
            hit_count,
            lng,
            lat,
            adong_code
        FROM ranked
        WHERE rn = 1
        ORDER BY normalized_query
        {limit_sql}
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return [
            GeocodeCacheRow(
                normalized_query=str(row[0]),
                gu_code=row[1],
                ldong_code=row[2],
                jibun=row[3],
                hit_count=int(row[4] or 0),
                lng=float(row[5]) if row[5] is not None else None,
                lat=float(row[6]) if row[6] is not None else None,
                adong_code=row[7],
            )
            for row in cursor.fetchall()
        ]


def inspect_rent_deal_geocode_cache_source() -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE jibun IS NOT NULL AND trim(jibun) <> '') AS with_jibun,
                COUNT(*) FILTER (WHERE location IS NOT NULL) AS with_location,
                COUNT(DISTINCT (ldong_code || ':' || COALESCE(trim(jibun), '')))
                    FILTER (WHERE jibun IS NOT NULL AND trim(jibun) <> '') AS distinct_queries
            FROM rent_deal
            """
        )
        total, with_jibun, with_location, distinct_queries = cursor.fetchone()

    return {
        "source_version": SOURCE_VERSION,
        "rent_deal_total": int(total or 0),
        "rent_deal_with_jibun": int(with_jibun or 0),
        "rent_deal_with_location": int(with_location or 0),
        "distinct_queries": int(distinct_queries or 0),
        "cache_count": RentDealGeocodeCache.objects.count(),
    }


def rebuild_rent_deal_geocode_cache(*, dry_run: bool = False, limit: int | None = None) -> dict[str, Any]:
    source = inspect_rent_deal_geocode_cache_source()
    rows = _fetch_source_rows(limit=limit)
    now = timezone.now()
    success = sum(1 for row in rows if row.lng is not None and row.lat is not None)
    failed = len(rows) - success

    result = {
        "target": "rent_deal_geocode_cache",
        "source_version": SOURCE_VERSION,
        "dry_run": dry_run,
        "source": source,
        "loaded": len(rows),
        "success": success,
        "failed": failed,
        "limited": limit is not None,
        "completed": limit is None,
        "status": "success" if limit is None else "partial",
    }
    if dry_run:
        return result

    objects = [
        RentDealGeocodeCache(
            cache_key=_cache_key(row.normalized_query),
            normalized_query=row.normalized_query,
            gu_code=row.gu_code,
            ldong_code=row.ldong_code,
            jibun=row.jibun,
            provider="imported",
            status="success" if row.lng is not None and row.lat is not None else "failed",
            lng=row.lng,
            lat=row.lat,
            adong_code=row.adong_code if row.lng is not None and row.lat is not None else None,
            error=None if row.lng is not None and row.lat is not None else "no location in rent_deal source",
            hit_count=row.hit_count,
            first_seen_at=now,
            last_used_at=now,
            fetched_at=now,
            raw_response=None,
            created_at=now,
            updated_at=now,
        )
        for row in rows
    ]

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE rent_deal_geocode_cache")
        RentDealGeocodeCache.objects.bulk_create(objects, batch_size=BATCH_SIZE)

    result["cache_count"] = RentDealGeocodeCache.objects.count()
    return result
