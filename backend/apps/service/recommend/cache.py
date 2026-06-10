from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db import connection
from django.utils import timezone

from apps.service.recommend.models import RecommendRentRegionCache


RENT_CACHE_SCOPE = "recent_365d"
RENT_CACHE_SOURCE_VERSION = "recommend-rent-v1"


def _code_column(region_level: str) -> str:
    if region_level == "adong":
        return "adong_code"
    if region_level == "ldong":
        return "ldong_code"
    raise ValueError("region_level must be adong or ldong")


def _period_key(conversion_rate_period: Any) -> str:
    return str(conversion_rate_period or "")


def rebuild_recommend_rent_cache(
    *,
    region_levels: tuple[str, ...] = ("adong", "ldong"),
    monthly_rate: float,
    conversion_rate_period: Any,
    as_of_date: date | None = None,
) -> dict[str, int]:
    as_of = as_of_date or timezone.localdate()
    recent_from = as_of - timedelta(days=365)
    period_key = _period_key(conversion_rate_period)
    computed_at = timezone.now()
    counts: dict[str, int] = {}

    for region_level in region_levels:
        code_column = _code_column(region_level)
        sql = f"""
            INSERT INTO recommend_rent_region_cache (
                cache_key,
                region_type,
                region_code,
                scope,
                as_of_date,
                recent_from,
                conversion_rate_period,
                monthly_rate,
                deal_count,
                avg_per_m2,
                median_converted,
                min_contract_date,
                max_contract_date,
                source_version,
                computed_at
            )
            SELECT
                CONCAT(%s, ':', {code_column}, ':', %s, ':', %s, ':', %s) AS cache_key,
                %s AS region_type,
                {code_column} AS region_code,
                %s AS scope,
                %s AS as_of_date,
                %s AS recent_from,
                %s AS conversion_rate_period,
                %s AS monthly_rate,
                COUNT(*)::integer AS deal_count,
                AVG((monthly_rent + deposit * %s) / NULLIF(area_m2, 0))
                    FILTER (WHERE area_m2 IS NOT NULL AND area_m2 > 0) AS avg_per_m2,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (monthly_rent + deposit * %s)) AS median_converted,
                MIN(contract_date) AS min_contract_date,
                MAX(contract_date) AS max_contract_date,
                %s AS source_version,
                %s AS computed_at
            FROM rent_deal
            WHERE {code_column} IS NOT NULL
              AND contract_date >= %s
            GROUP BY {code_column}
            ON CONFLICT (cache_key) DO UPDATE SET
                deal_count = EXCLUDED.deal_count,
                avg_per_m2 = EXCLUDED.avg_per_m2,
                median_converted = EXCLUDED.median_converted,
                min_contract_date = EXCLUDED.min_contract_date,
                max_contract_date = EXCLUDED.max_contract_date,
                monthly_rate = EXCLUDED.monthly_rate,
                recent_from = EXCLUDED.recent_from,
                source_version = EXCLUDED.source_version,
                computed_at = EXCLUDED.computed_at
        """
        params = [
            region_level,
            RENT_CACHE_SCOPE,
            as_of.isoformat(),
            period_key,
            region_level,
            RENT_CACHE_SCOPE,
            as_of,
            recent_from,
            period_key,
            monthly_rate,
            monthly_rate,
            monthly_rate,
            RENT_CACHE_SOURCE_VERSION,
            computed_at,
            recent_from,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
        counts[region_level] = RecommendRentRegionCache.objects.filter(
            region_type=region_level,
            scope=RENT_CACHE_SCOPE,
            as_of_date=as_of,
            conversion_rate_period=period_key,
            source_version=RENT_CACHE_SOURCE_VERSION,
        ).count()
    return counts


def load_rent_metrics(
    *,
    region_level: str,
    monthly_rate: float,
    conversion_rate_period: Any,
    as_of_date: date | None = None,
) -> dict[str, dict[str, float | int | None]]:
    as_of = as_of_date or timezone.localdate()
    period_key = _period_key(conversion_rate_period)
    queryset = RecommendRentRegionCache.objects.filter(
        region_type=region_level,
        scope=RENT_CACHE_SCOPE,
        as_of_date=as_of,
        conversion_rate_period=period_key,
        source_version=RENT_CACHE_SOURCE_VERSION,
    )
    if not queryset.exists():
        rebuild_recommend_rent_cache(
            region_levels=(region_level,),
            monthly_rate=monthly_rate,
            conversion_rate_period=period_key,
            as_of_date=as_of,
        )
        queryset = RecommendRentRegionCache.objects.filter(
            region_type=region_level,
            scope=RENT_CACHE_SCOPE,
            as_of_date=as_of,
            conversion_rate_period=period_key,
            source_version=RENT_CACHE_SOURCE_VERSION,
        )

    return {
        str(row.region_code): {
            "deal_count": row.deal_count,
            "avg_per_m2": row.avg_per_m2,
            "median_converted": row.median_converted,
        }
        for row in queryset
    }
