from __future__ import annotations

import time

from apps.dashboard.cache.models import DashboardAdongCache, DashboardLdongCache
from apps.public_data.regions.models import Adong, Ldong


SUMMARY_KEYWORDS = ("어때", "정보", "요약", "살기", "특징", "알려줘")
DETAIL_KEYWORDS = (
    "월세",
    "전세",
    "매물",
    "거래",
    "실거래",
    "보증금",
    "운영시간",
    "영업시간",
    "도서관",
    "카페",
    "편의점",
    "공원",
    "지하철",
    "버스",
    "목록",
    "몇 개",
    "몇개",
)


def _is_summary_question(question: str) -> bool:
    if not any(keyword in question for keyword in SUMMARY_KEYWORDS):
        return False
    return not any(keyword in question for keyword in DETAIL_KEYWORDS)


def _find_region(question: str):
    ldongs = (
        Ldong.objects.select_related("gu")
        .filter(name__isnull=False)
        .only("ldong_code", "name", "slug", "gu__name")
    )
    matched_ldongs = [
        region for region in ldongs
        if region.name and region.name in question
    ]
    if matched_ldongs:
        return "ldong", sorted(
            matched_ldongs,
            key=lambda item: len(item.name),
            reverse=True,
        )[0]

    adongs = (
        Adong.objects.select_related("gu")
        .filter(name__isnull=False)
        .only("adong_code", "name", "slug", "gu__name")
    )
    matched_adongs = [
        region for region in adongs
        if region.name and region.name in question
    ]
    if matched_adongs:
        return "adong", sorted(
            matched_adongs,
            key=lambda item: len(item.name),
            reverse=True,
        )[0]

    return None, None


def _text_from_section(section: dict) -> str:
    if not isinstance(section, dict):
        return ""

    overview = section.get("overview") or {}
    if not isinstance(overview, dict):
        return ""

    return overview.get("headline") or overview.get("summary") or ""


def _build_response(region_type: str, region, cache, start: float) -> dict:
    payload = cache.dashboard_payload or {}

    intro = payload.get("intro") or cache.intro or ""
    rent = _text_from_section(payload.get("rent_summary") or {})
    transit = _text_from_section(payload.get("transit_summary") or {})
    infra = _text_from_section(payload.get("infra_summary") or {})
    safety = _text_from_section(payload.get("safety_summary") or {})

    gu_name = region.gu.name if getattr(region, "gu", None) else ""
    dong_name = region.name
    region_label = "행정동" if region_type == "adong" else "법정동"

    answer = intro or (
        f"{dong_name}은 서울 {gu_name}에 있는 동네입니다. "
        "대시보드에 저장된 요약 정보를 기준으로 월세, 교통, 생활시설, 안전 정보를 간단히 정리했어요."
    )

    columns = {
        "구": gu_name,
        "동네 유형": region_label,
    }

    if rent:
        columns["월세"] = rent
    if transit:
        columns["교통"] = transit
    if infra:
        columns["생활시설"] = infra
    if safety:
        columns["안전"] = safety

    return {
        "answer": answer,
        "neighborhoods": [],
        "visualizations": [
            {
                "type": "table",
                "title": f"{dong_name} 대시보드 요약",
                "unit": "",
                "data": [
                    {
                        "label": dong_name,
                        "value": None,
                        "columns": columns,
                    }
                ],
            }
        ],
        "route": "dashboard_cache",
        "query_type": "info",
        "sql": None,
        "sql_attempts": 0,
        "elapsed_sec": round(time.time() - start, 2),
    }


def try_dashboard_cache_answer(question: str, start: float) -> dict | None:
    if not _is_summary_question(question):
        return None

    region_type, region = _find_region(question)
    if not region:
        return None

    if region_type == "ldong":
        cache = DashboardLdongCache.objects.filter(ldong=region).first()
    else:
        cache = DashboardAdongCache.objects.filter(adong=region).first()

    if not cache:
        return None

    return _build_response(region_type, region, cache, start)
