from __future__ import annotations

import json
import math
import os
from functools import lru_cache
from urllib.parse import urlencode
from urllib.request import urlopen

from django.core.cache import cache


FALLBACK_ANNUAL_CONVERSION_RATE = 6.0


def _parse_number(value: object) -> float | None:
    try:
        text = str(value).replace(",", "").strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=1)
def _kosis_rate_from_api() -> float | None:
    api_key = os.environ.get("KOSIS_API_KEY", "").strip()
    if not api_key:
        return None
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
    try:
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return None
    rows = payload if isinstance(payload, list) else []
    latest_prd = max((str(row.get("PRD_DE") or "") for row in rows), default="")
    values = [
        value
        for row in rows
        if str(row.get("PRD_DE") or "") == latest_prd
        for value in [_parse_number(row.get("DT"))]
        if value is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def get_annual_conversion_rate() -> float:
    cached = cache.get("rent:kosis_annual_conversion_rate:v1")
    if cached is not None:
        return float(cached)
    rate = _kosis_rate_from_api() or FALLBACK_ANNUAL_CONVERSION_RATE
    cache.set("rent:kosis_annual_conversion_rate:v1", rate, timeout=60 * 60 * 24)
    return float(rate)


def get_monthly_conversion_rate() -> float:
    return get_annual_conversion_rate() / 100.0 / 12.0


def convert_to_monthly(deposit: float, monthly_rent: float) -> int:
    d = max(0.0, float(deposit))
    m = max(0.0, float(monthly_rent))
    return int(math.floor(m + d * get_monthly_conversion_rate()))
