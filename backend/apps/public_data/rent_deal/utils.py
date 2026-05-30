from __future__ import annotations

import json
import math
import os
from decimal import Decimal
from functools import lru_cache
from urllib.parse import urlencode
from urllib.request import urlopen

from django.core.cache import cache

from apps.public_data.rent_deal.models import RentConversionRate


FALLBACK_ANNUAL_CONVERSION_RATE = 6.0
CONVERSION_RATE_SOURCE = "KOSIS \ud55c\uad6d\ubd80\ub3d9\uc0b0\uc6d0 \uc804\uc6d4\uc138\uc804\ud658\uc728"
CONVERSION_RATE_CACHE_KEY = "rent:kosis_annual_conversion_rate:v2"


def _parse_number(value: object) -> float | None:
    try:
        text = str(value).replace(",", "").strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _kosis_rows_from_api() -> list[dict]:
    api_key = os.environ.get("KOSIS_API_KEY", "").strip()
    if not api_key:
        return []
    params = {
        "method": "getList",
        "apiKey": api_key,
        "itmId": "T1+",
        "objL1": "ALL",
        "objL2": "a7+",
        "objL3": "",
        "objL4": "",
        "objL5": "",
        "objL6": "",
        "objL7": "",
        "objL8": "",
        "format": "json",
        "jsonVD": "Y",
        "prdSe": "M",
        "newEstPrdCnt": "3",
        "orgId": "408",
        "tblId": "DT_30404_N0010",
    }
    url = "https://kosis.kr/openapi/Param/statisticsParameterData.do?" + urlencode(params)
    with urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    return payload if isinstance(payload, list) else []


def _rate_payload_from_rows(rows: list[dict]) -> dict | None:
    latest_prd = max((str(row.get("PRD_DE") or "") for row in rows), default="")
    values = [
        value
        for row in rows
        if str(row.get("PRD_DE") or "") == latest_prd
        for value in [_parse_number(row.get("DT"))]
        if value is not None
    ]
    if not latest_prd or not values:
        return None
    annual_rate = round(sum(values) / len(values), 3)
    return {
        "period_ym": latest_prd,
        "annual_rate": annual_rate,
        "monthly_rate": annual_rate / 100.0 / 12.0,
        "source": CONVERSION_RATE_SOURCE,
        "unit": "percent_per_year",
        "is_fallback": False,
        "raw_payload": {"rows": [row for row in rows if str(row.get("PRD_DE") or "") == latest_prd]},
    }


def refresh_conversion_rate_from_kosis() -> RentConversionRate | None:
    try:
        payload = _rate_payload_from_rows(_kosis_rows_from_api())
    except Exception:
        return None
    if not payload:
        return None
    obj, _created = RentConversionRate.objects.update_or_create(
        period_ym=payload["period_ym"],
        defaults={
            "annual_rate": Decimal(str(payload["annual_rate"])),
            "source": payload["source"],
            "raw_payload": payload["raw_payload"],
        },
    )
    cache.delete(CONVERSION_RATE_CACHE_KEY)
    _kosis_rate_from_api.cache_clear()
    return obj


def _latest_rate_from_db() -> RentConversionRate | None:
    return RentConversionRate.objects.order_by("-period_ym").first()


def _payload_from_db(obj: RentConversionRate) -> dict:
    annual_rate = float(obj.annual_rate)
    return {
        "annual_rate": annual_rate,
        "monthly_rate": annual_rate / 100.0 / 12.0,
        "period_ym": obj.period_ym,
        "source": obj.source,
        "unit": "percent_per_year",
        "is_fallback": False,
        "fetched_at": obj.fetched_at.isoformat() if obj.fetched_at else None,
    }


def get_conversion_rate_payload(*, refresh_if_missing: bool = True) -> dict:
    cached = cache.get(CONVERSION_RATE_CACHE_KEY)
    if cached is not None:
        return dict(cached)
    obj = _latest_rate_from_db()
    if obj is None and refresh_if_missing:
        obj = refresh_conversion_rate_from_kosis()
    if obj is not None:
        payload = _payload_from_db(obj)
    else:
        annual_rate = FALLBACK_ANNUAL_CONVERSION_RATE
        payload = {
            "annual_rate": annual_rate,
            "monthly_rate": annual_rate / 100.0 / 12.0,
            "period_ym": None,
            "source": CONVERSION_RATE_SOURCE,
            "unit": "percent_per_year",
            "is_fallback": True,
            "fetched_at": None,
        }
    cache.set(CONVERSION_RATE_CACHE_KEY, payload, timeout=60 * 60 * 24)
    return payload


@lru_cache(maxsize=1)
def _kosis_rate_from_api() -> float | None:
    obj = refresh_conversion_rate_from_kosis()
    return float(obj.annual_rate) if obj else None


def get_annual_conversion_rate() -> float:
    return float(get_conversion_rate_payload()["annual_rate"])


def get_monthly_conversion_rate() -> float:
    return float(get_conversion_rate_payload()["monthly_rate"])


def convert_to_monthly(deposit: float, monthly_rent: float) -> int:
    d = max(0.0, float(deposit))
    m = max(0.0, float(monthly_rent))
    return int(math.floor(m + d * get_monthly_conversion_rate()))
