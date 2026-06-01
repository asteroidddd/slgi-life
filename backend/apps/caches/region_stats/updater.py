from __future__ import annotations

from typing import Any

from django.db import connection, transaction
from django.utils import timezone

from apps.caches.region_stats.models import RegionAmenityCategoryCache, RegionParkAreaCache


SOURCE_VERSION = "region-stats-cache-v1"
REGIONS = (
    ("seoul", "seoul", "code"),
    ("gu", "gu", "gu_code"),
    ("ldong", "ldong", "ldong_code"),
    ("adong", "adong", "adong_code"),
)


def _fetch_one(sql: str, params: list[Any] | None = None) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
    return dict(zip(columns, row)) if row else {}


def _insert_park_area_for_region(
    *,
    region_type: str,
    region_table: str,
    code_col: str,
    now_iso: str,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO region_park_area_cache (
                cache_key,
                region_type,
                region_code,
                park_count,
                park_area_m2,
                region_area_m2,
                park_area_ratio,
                source_version,
                computed_at,
                created_at,
                updated_at
            )
            SELECT
                %s || ':' || r.{code_col},
                %s,
                r.{code_col},
                COUNT(DISTINCT p.id)::integer,
                COALESCE(
                    SUM(
                        CASE
                            WHEN p.id IS NULL THEN 0
                            ELSE ST_Area(
                                ST_Intersection(
                                    ST_MakeValid(r.boundary),
                                    ST_MakeValid(p.boundary)
                                )::geography
                            )
                        END
                    ),
                    0
                )::float AS park_area_m2,
                COALESCE(r.area_m2::float, ST_Area(r.boundary::geography)::float) AS region_area_m2,
                CASE
                    WHEN COALESCE(r.area_m2::float, ST_Area(r.boundary::geography)::float) > 0 THEN
                        COALESCE(
                            SUM(
                                CASE
                                    WHEN p.id IS NULL THEN 0
                                    ELSE ST_Area(
                                        ST_Intersection(
                                            ST_MakeValid(r.boundary),
                                            ST_MakeValid(p.boundary)
                                        )::geography
                                    )
                                END
                            ),
                            0
                        )::float
                        / COALESCE(r.area_m2::float, ST_Area(r.boundary::geography)::float)
                    ELSE 0
                END AS park_area_ratio,
                %s,
                %s::timestamptz,
                %s::timestamptz,
                %s::timestamptz
            FROM {region_table} r
            LEFT JOIN park p
              ON r.boundary IS NOT NULL
             AND p.boundary IS NOT NULL
             AND ST_Intersects(r.boundary, p.boundary)
            WHERE r.boundary IS NOT NULL
            GROUP BY r.{code_col}, r.area_m2, r.boundary
            """,
            [region_type, region_type, SOURCE_VERSION, now_iso, now_iso, now_iso],
        )
        return cursor.rowcount


def rebuild_region_park_area_cache(*, dry_run: bool = False) -> dict[str, Any]:
    before = RegionParkAreaCache.objects.count()
    result: dict[str, Any] = {
        "target": "region_park_area_cache",
        "source_version": SOURCE_VERSION,
        "dry_run": dry_run,
        "before_count": before,
        "regions": {},
        "completed": True,
        "status": "success",
    }
    if dry_run:
        return result

    now = timezone.now()
    now_iso = now.isoformat()
    inserted_total = 0
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE region_park_area_cache")
        for region_type, table, code_col in REGIONS:
            inserted = _insert_park_area_for_region(
                region_type=region_type,
                region_table=table,
                code_col=code_col,
                now_iso=now_iso,
            )
            result["regions"][region_type] = inserted
            inserted_total += inserted

    result["inserted"] = inserted_total
    result["after_count"] = RegionParkAreaCache.objects.count()
    return result


def _insert_amenity_for_seoul(now_iso: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO region_amenity_category_cache (
                cache_key,
                region_type,
                region_code,
                category,
                amenity_count,
                density_per_km2,
                region_area_m2,
                source_version,
                computed_at,
                created_at,
                updated_at
            )
            SELECT
                'seoul:' || s.code || ':' || a.category,
                'seoul',
                s.code,
                a.category,
                COUNT(DISTINCT a.id)::integer,
                CASE
                    WHEN s.area_m2 > 0 THEN COUNT(DISTINCT a.id)::float / (s.area_m2::float / 1000000.0)
                    ELSE NULL
                END,
                s.area_m2::float,
                %s,
                %s::timestamptz,
                %s::timestamptz,
                %s::timestamptz
            FROM seoul s
            CROSS JOIN amenity a
            GROUP BY s.code, s.area_m2, a.category
            """,
            [SOURCE_VERSION, now_iso, now_iso, now_iso],
        )
        return cursor.rowcount


def _insert_amenity_for_gu(now_iso: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO region_amenity_category_cache (
                cache_key,
                region_type,
                region_code,
                category,
                amenity_count,
                density_per_km2,
                region_area_m2,
                source_version,
                computed_at,
                created_at,
                updated_at
            )
            SELECT
                'gu:' || g.gu_code || ':' || a.category,
                'gu',
                g.gu_code,
                a.category,
                COUNT(DISTINCT aa.amenity_id)::integer,
                CASE
                    WHEN g.area_m2 > 0 THEN COUNT(DISTINCT aa.amenity_id)::float / (g.area_m2::float / 1000000.0)
                    ELSE NULL
                END,
                g.area_m2::float,
                %s,
                %s::timestamptz,
                %s::timestamptz,
                %s::timestamptz
            FROM gu g
            JOIN adong d ON d.gu_code = g.gu_code
            JOIN amenity_adong aa ON aa.adong_code = d.adong_code
            JOIN amenity a ON a.id = aa.amenity_id
            GROUP BY g.gu_code, g.area_m2, a.category
            """,
            [SOURCE_VERSION, now_iso, now_iso, now_iso],
        )
        return cursor.rowcount


def _insert_amenity_for_region(
    *,
    region_type: str,
    region_table: str,
    code_col: str,
    link_table: str,
    link_code_col: str,
    now_iso: str,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO region_amenity_category_cache (
                cache_key,
                region_type,
                region_code,
                category,
                amenity_count,
                density_per_km2,
                region_area_m2,
                source_version,
                computed_at,
                created_at,
                updated_at
            )
            SELECT
                %s || ':' || r.{code_col} || ':' || a.category,
                %s,
                r.{code_col},
                a.category,
                COUNT(DISTINCT l.amenity_id)::integer,
                CASE
                    WHEN r.area_m2 > 0 THEN COUNT(DISTINCT l.amenity_id)::float / (r.area_m2::float / 1000000.0)
                    ELSE NULL
                END,
                r.area_m2::float,
                %s,
                %s::timestamptz,
                %s::timestamptz,
                %s::timestamptz
            FROM {region_table} r
            JOIN {link_table} l ON l.{link_code_col} = r.{code_col}
            JOIN amenity a ON a.id = l.amenity_id
            GROUP BY r.{code_col}, r.area_m2, a.category
            """,
            [region_type, region_type, SOURCE_VERSION, now_iso, now_iso, now_iso],
        )
        return cursor.rowcount


def rebuild_region_amenity_category_cache(*, dry_run: bool = False) -> dict[str, Any]:
    before = RegionAmenityCategoryCache.objects.count()
    result: dict[str, Any] = {
        "target": "region_amenity_category_cache",
        "source_version": SOURCE_VERSION,
        "dry_run": dry_run,
        "before_count": before,
        "regions": {},
        "completed": True,
        "status": "success",
    }
    if dry_run:
        return result

    now = timezone.now()
    now_iso = now.isoformat()
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE region_amenity_category_cache")
        result["regions"]["seoul"] = _insert_amenity_for_seoul(now_iso)
        result["regions"]["gu"] = _insert_amenity_for_gu(now_iso)
        result["regions"]["ldong"] = _insert_amenity_for_region(
            region_type="ldong",
            region_table="ldong",
            code_col="ldong_code",
            link_table="amenity_ldong",
            link_code_col="ldong_code",
            now_iso=now_iso,
        )
        result["regions"]["adong"] = _insert_amenity_for_region(
            region_type="adong",
            region_table="adong",
            code_col="adong_code",
            link_table="amenity_adong",
            link_code_col="adong_code",
            now_iso=now_iso,
        )

    result["inserted"] = sum(result["regions"].values())
    result["after_count"] = RegionAmenityCategoryCache.objects.count()
    return result


def update_all(*, dry_run: bool = False) -> dict[str, Any]:
    targets = {
        "region_park_area_cache": rebuild_region_park_area_cache(dry_run=dry_run),
        "region_amenity_category_cache": rebuild_region_amenity_category_cache(dry_run=dry_run),
    }
    return {
        "target": "region_stats_caches",
        "dry_run": dry_run,
        "targets": targets,
        "completed": all(item.get("completed") for item in targets.values()),
        "status": "success",
    }


def inspect_region_stats_cache() -> dict[str, Any]:
    return {
        "source_version": SOURCE_VERSION,
        "park_area_count": RegionParkAreaCache.objects.count(),
        "amenity_category_count": RegionAmenityCategoryCache.objects.count(),
        "source_counts": {
            "park": _fetch_one("SELECT COUNT(*) AS count FROM park").get("count"),
            "amenity": _fetch_one("SELECT COUNT(*) AS count FROM amenity").get("count"),
            "amenity_adong": _fetch_one("SELECT COUNT(*) AS count FROM amenity_adong").get("count"),
            "amenity_ldong": _fetch_one("SELECT COUNT(*) AS count FROM amenity_ldong").get("count"),
        },
    }
