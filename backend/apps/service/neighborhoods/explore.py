"""SPEC 6.3 후속 — 자취 시세 BI 대시보드 (`/adong/<slug>/explore`).

GET /api/adongs/<slug>/explore?<filters>

필터 (모두 선택)
----------------
- deal_types : "villa,dagagu,danok,officetel,apt" 콤마 구분 (default 자취 4종)
- period     : "3m" | "6m" | "12m" | "24m" | "all"  (default "6m")
- deposit_min / deposit_max : 만원 (default 0 / 50000)
- monthly_min / monthly_max : 만원 (default 0 / 300)
- area_min / area_max       : m² (default 10 / 100)
- page       : 1-indexed (default 1)
- page_size  : 20 (max 100)
- sort       : "date_desc" | "date_asc" | "deposit_desc" | "deposit_asc" |
               "monthly_desc" | "monthly_asc" | "converted_desc" | "converted_asc" |
               "area_desc" | "area_asc"
               (default "date_desc")

응답
----
- adong:            { slug, name, gu }
- filters_applied: 적용된 필터 정규화 dict (UI 동기화 용)
- kpi:             { count, avg_converted_rent, min_deposit, avg_area_m2 }
- type_avg:        [{deal_type, label, avg_converted_rent, count}, ...]  (4 자취 + apt)
- scatter:         [{deal_type, area_m2, converted_rent}, ...]  (최대 500건)
- deposit_band:    [{band, count, avg_monthly_rent}, ...]
- monthly_trend:   [{month, villa, dagagu, danok, officetel}, ...]
- deals:           { items: [...], total, page, page_size, total_pages }

성능
----
- 한 동 거래량 7.4M / 426 = 평균 17k. 6개월 자취만 ≈ 1~3k → 인덱스 충분.
- KPI/type_avg/deposit_band/monthly_trend 는 SQL aggregation 한 방.
- scatter 500건은 sample, deals 는 페이지네이션.

RentDeal scope
--------------
- Uses only rent_deal rows with confirmed adong_code for the selected adong.
- Response keys are preserved for the frontend contract.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import Avg, Count, F, Min, Value
from django.db.models.expressions import Expression
from django.db.models.query import QuerySet
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from apps.public_data.rent_deal.models import (
    DEAL_TYPE_TO_HOUSING_TYPE,
    HOUSING_TYPE_TO_DEAL_TYPE,
    RentDeal,
)


# ---------------------------------------------------------------------------
# 상수 / 사전
# ---------------------------------------------------------------------------

ALL_DEAL_TYPES: tuple[str, ...] = ("villa", "dagagu", "danok", "officetel", "apt")
STUDIO_DEFAULT_TYPES: tuple[str, ...] = ("villa", "dagagu", "danok", "officetel")

DEAL_TYPE_LABEL: dict[str, str] = {
    "villa": "연립다세대",
    "dagagu": "다가구",
    "danok": "단독",
    "officetel": "오피스텔",
    "apt": "아파트",
}

PERIOD_TO_DAYS: dict[str, int | None] = {
    "3m": 90,
    "6m": 180,
    "12m": 365,
    "24m": 730,
    "all": None,
}

SORT_TO_ORDER: dict[str, tuple[str, ...]] = {
    "date_desc": ("-contract_date", "-id"),
    "date_asc": ("contract_date", "id"),
    "deposit_desc": ("-deposit", "-contract_date"),
    "deposit_asc": ("deposit", "-contract_date"),
    "monthly_desc": ("-monthly_rent", "-contract_date"),
    "monthly_asc": ("monthly_rent", "-contract_date"),
    # 환산월세는 SQL 표현식으로 정렬해야 해서 별도 처리 (apply_sort).
    "converted_desc": ("__converted_desc",),
    "converted_asc": ("__converted_asc",),
    "area_desc": ("-area_m2",),
    "area_asc": ("area_m2",),
}

DEPOSIT_BANDS: list[tuple[str, int, int]] = [
    ("0", 0, 250),
    ("500", 250, 750),
    ("1000", 750, 1500),
    ("2000", 1500, 2500),
    ("3000+", 2500, 10**9),
]

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20
SCATTER_SAMPLE_SIZE = 500
TREND_KEYS = ("villa", "dagagu", "danok", "officetel")


# ---------------------------------------------------------------------------
# 필터 파싱
# ---------------------------------------------------------------------------

def _parse_csv_set(raw: str | None, allowed: tuple[str, ...]) -> tuple[str, ...]:
    if not raw:
        return ()
    items = [s.strip() for s in raw.split(",") if s.strip()]
    bad = [s for s in items if s not in allowed]
    if bad:
        raise ValidationError(
            {"deal_types": f"알 수 없는 유형: {bad}. 허용: {list(allowed)}"}
        )
    # dedupe & 순서 보존
    seen = set()
    out: list[str] = []
    for s in items:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return tuple(out)


def _parse_int(
    raw: str | None, key: str, default: int, lo: int, hi: int
) -> int:
    if raw is None or raw == "":
        return default
    try:
        v = int(raw)
    except ValueError as exc:
        raise ValidationError({key: f"{key}는 정수여야 합니다."}) from exc
    if v < lo or v > hi:
        raise ValidationError(
            {key: f"{key}는 {lo}~{hi} 범위여야 합니다 (입력: {v})."}
        )
    return v


def parse_base_filters(request: Request) -> dict[str, Any]:
    """공통 자취 거래량 필터 파싱 (deal_types/period/deposit/monthly/area).

    Explore 와 Match 양쪽이 공유 (eng-review #17). sort/page/page_size 는 explore
    only — `parse_explore_filters` 에서 추가.
    """
    p = request.query_params

    deal_types = _parse_csv_set(p.get("deal_types"), ALL_DEAL_TYPES)
    if not deal_types:
        deal_types = STUDIO_DEFAULT_TYPES

    period = p.get("period", "6m")
    if period not in PERIOD_TO_DAYS:
        raise ValidationError(
            {"period": f"period는 {list(PERIOD_TO_DAYS.keys())} 중 하나여야 합니다."}
        )

    deposit_min = _parse_int(p.get("deposit_min"), "deposit_min", 0, 0, 10_000_000)
    deposit_max = _parse_int(
        p.get("deposit_max"), "deposit_max", 50_000, 0, 10_000_000
    )
    if deposit_min > deposit_max:
        raise ValidationError(
            {"deposit_min": "deposit_min은 deposit_max 이하여야 합니다."}
        )

    monthly_min = _parse_int(p.get("monthly_min"), "monthly_min", 0, 0, 1_000_000)
    monthly_max = _parse_int(p.get("monthly_max"), "monthly_max", 300, 0, 1_000_000)
    if monthly_min > monthly_max:
        raise ValidationError(
            {"monthly_min": "monthly_min은 monthly_max 이하여야 합니다."}
        )

    area_min = _parse_int(p.get("area_min"), "area_min", 10, 0, 10_000)
    area_max = _parse_int(p.get("area_max"), "area_max", 100, 0, 10_000)
    if area_min > area_max:
        raise ValidationError({"area_min": "area_min은 area_max 이하여야 합니다."})

    return {
        "deal_types": deal_types,
        "period": period,
        "deposit_min": deposit_min,
        "deposit_max": deposit_max,
        "monthly_min": monthly_min,
        "monthly_max": monthly_max,
        "area_min": area_min,
        "area_max": area_max,
    }


def parse_explore_filters(request: Request) -> dict[str, Any]:
    """쿼리 파라미터 → 정규화된 explore 필터 dict (base + sort/page)."""
    base = parse_base_filters(request)
    p = request.query_params

    page = _parse_int(p.get("page"), "page", 1, 1, 100_000)
    page_size = _parse_int(p.get("page_size"), "page_size", DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)

    sort = p.get("sort", "date_desc")
    if sort not in SORT_TO_ORDER:
        raise ValidationError(
            {"sort": f"sort는 {list(SORT_TO_ORDER.keys())} 중 하나여야 합니다."}
        )

    return {
        **base,
        "page": page,
        "page_size": page_size,
        "sort": sort,
    }


# ---------------------------------------------------------------------------
# 쿼리셋 + 집계
# ---------------------------------------------------------------------------

CONVERTED_EXPR: Expression = F("monthly_rent") + F("deposit") * Value(0.005)


def apply_base_filters(
    qs: QuerySet[RentDeal], filters: dict[str, Any], today: date
) -> QuerySet[RentDeal]:
    """adong 무관 base 필터만 적용 (match-counts 가 모든 동 GROUP BY 위해 사용).

    sub-plan 4.5D: deal_type 영문 enum → housing_type 한글 raw 변환. deal_date → contract_date.
    """
    # 응답 'deal_types' 영문 enum → DB 한글 housing_type 변환 (lock 1).
    housing_types = [
        DEAL_TYPE_TO_HOUSING_TYPE[k]
        for k in filters["deal_types"]
        if k in DEAL_TYPE_TO_HOUSING_TYPE
    ]
    qs = qs.filter(
        housing_type__in=housing_types,
        deposit__gte=filters["deposit_min"],
        deposit__lte=filters["deposit_max"],
        monthly_rent__gte=filters["monthly_min"],
        monthly_rent__lte=filters["monthly_max"],
        area_m2__gte=filters["area_min"],
        area_m2__lte=filters["area_max"],
    )
    days = PERIOD_TO_DAYS[filters["period"]]
    if days is not None:
        from datetime import timedelta

        qs = qs.filter(contract_date__gte=today - timedelta(days=days))
    return qs


def apply_filters(
    qs: QuerySet[RentDeal], adong_code: str, filters: dict[str, Any], today: date
) -> QuerySet[RentDeal]:
    """Filter deals for one adong using confirmed rent_deal.adong_code only."""
    return apply_base_filters(qs.filter(adong_id=adong_code), filters, today)


def compute_kpi(qs: QuerySet[RentDeal]) -> dict[str, Any]:
    agg = qs.aggregate(
        n=Count("id"),
        avg_rent=Avg(CONVERTED_EXPR),
        min_deposit=Min("deposit"),
        avg_area=Avg("area_m2"),
    )
    return {
        "count": int(agg["n"] or 0),
        "avg_converted_rent": int(round(float(agg["avg_rent"])))
        if agg["avg_rent"] is not None
        else None,
        "min_deposit": int(agg["min_deposit"]) if agg["min_deposit"] is not None else None,
        "avg_area_m2": round(float(agg["avg_area"]), 1)
        if agg["avg_area"] is not None
        else None,
    }


def compute_type_avg(qs: QuerySet[RentDeal], deal_types: tuple[str, ...]) -> list[dict]:
    """sub-plan 4.5D: DB housing_type 한글 GROUP BY → 영문 enum 매핑."""
    rows = list(
        qs.values("housing_type").annotate(
            avg_converted=Avg(CONVERTED_EXPR), n=Count("id")
        )
    )
    # DB 한글 → 영문 enum 매핑 (응답 key 'deal_type' 보존).
    by_type: dict[str, dict] = {}
    for r in rows:
        en = HOUSING_TYPE_TO_DEAL_TYPE.get(r["housing_type"])
        if en is not None:
            by_type[en] = r
    out = []
    for key in deal_types:  # 사용자가 선택한 유형만, 선택 순서 유지
        rec = by_type.get(key)
        if rec and rec["n"] >= 3:
            out.append(
                {
                    "deal_type": key,
                    "label": DEAL_TYPE_LABEL[key],
                    "avg_converted_rent": int(round(float(rec["avg_converted"]))),
                    "count": rec["n"],
                }
            )
        else:
            out.append(
                {
                    "deal_type": key,
                    "label": DEAL_TYPE_LABEL[key],
                    "avg_converted_rent": None,
                    "count": rec["n"] if rec else 0,
                }
            )
    return out


def compute_scatter(qs: QuerySet[RentDeal]) -> list[dict]:
    """sub-plan 4.5D: DB housing_type 한글 → 영문 enum 매핑. area_m2 NULL 제외."""
    rows = (
        qs.filter(area_m2__isnull=False)
        .order_by("-contract_date")
        .values("housing_type", "area_m2", "monthly_rent", "deposit")[:SCATTER_SAMPLE_SIZE]
    )
    out = []
    for r in rows:
        deal_type_en = HOUSING_TYPE_TO_DEAL_TYPE.get(r["housing_type"])
        if deal_type_en is None:
            continue
        converted = int(round(float(r["monthly_rent"]) + float(r["deposit"]) * 0.005))
        out.append(
            {
                "deal_type": deal_type_en,
                "area_m2": round(float(r["area_m2"]), 1),
                "converted_rent": converted,
            }
        )
    return out


def compute_deposit_band(qs: QuerySet[RentDeal]) -> list[dict]:
    out = []
    for label, lo, hi in DEPOSIT_BANDS:
        sub = qs.filter(deposit__gte=lo, deposit__lt=hi)
        agg = sub.aggregate(n=Count("id"), avg_rent=Avg("monthly_rent"))
        n = int(agg["n"] or 0)
        out.append(
            {
                "band": label,
                "count": n,
                "avg_monthly_rent": round(float(agg["avg_rent"]), 1)
                if n >= 3 and agg["avg_rent"] is not None
                else 0.0,
            }
        )
    return out


def compute_monthly_trend(qs: QuerySet[RentDeal], period: str, today: date) -> list[dict]:
    """월별 housing_type 평균 monthly_rent. period 가 길면 그 만큼 월 라벨 생성.

    sub-plan 4.5D: contract_date / housing_type 한글. 응답 key는 영문 enum 보존.
    """
    days = PERIOD_TO_DAYS[period] or 365  # all 일 때도 1년 그래프로 컷
    months = max(3, min(24, days // 30))

    seq: list[date] = []
    cur = date(today.year, today.month, 1)
    for _ in range(months):
        seq.append(cur)
        prev_m = cur.month - 1 or 12
        prev_y = cur.year if cur.month != 1 else cur.year - 1
        cur = date(prev_y, prev_m, 1)
    seq.reverse()

    rows = list(
        qs.extra(select={"month": "TO_CHAR(contract_date, 'YYYY-MM')"})
        .values("month", "housing_type")
        .annotate(avg_rent=Avg("monthly_rent"), n=Count("id"))
    )
    # (month, deal_type 영문 enum) → (avg, n) — 응답 dict key 영문 보존.
    by_key: dict[tuple[str, str], tuple[float | None, int]] = {}
    for r in rows:
        en = HOUSING_TYPE_TO_DEAL_TYPE.get(r["housing_type"])
        if en is None:
            continue
        by_key[(r["month"], en)] = (r["avg_rent"], r["n"])

    out = []
    for d in seq:
        m_label = f"{d.year:04d}-{d.month:02d}"
        entry: dict = {"month": m_label}
        for key in TREND_KEYS:
            rec = by_key.get((m_label, key))
            if rec is None or rec[1] < 3:
                entry[key] = None
            else:
                entry[key] = round(float(rec[0]), 1)
        out.append(entry)
    return out


def paginate_deals(
    qs: QuerySet[RentDeal], filters: dict[str, Any]
) -> dict[str, Any]:
    sort = filters["sort"]
    page = filters["page"]
    page_size = filters["page_size"]

    sort_key = SORT_TO_ORDER[sort]
    if sort_key[0] == "__converted_desc":
        qs = qs.annotate(__c=CONVERTED_EXPR).order_by("-__c", "-contract_date")
    elif sort_key[0] == "__converted_asc":
        qs = qs.annotate(__c=CONVERTED_EXPR).order_by("__c", "-contract_date")
    else:
        qs = qs.order_by(*sort_key)

    total = qs.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size

    items = []
    # sub-plan 4.5D: contract_date / construction_year 컬럼명 정합.
    # 응답 dict 'date'/'build_year'/'deal_type' key는 보존 (frontend lock 1).
    for r in qs.values(
        "contract_date",
        "housing_type",
        "area_m2",
        "deposit",
        "monthly_rent",
        "house_name",
        "construction_year",
        "floor",
    )[start:end]:
        deal_type_en = HOUSING_TYPE_TO_DEAL_TYPE.get(r["housing_type"], "")
        converted = int(
            round(float(r["monthly_rent"]) + float(r["deposit"]) * 0.005)
        )
        area_val = (
            round(float(r["area_m2"]), 1) if r["area_m2"] is not None else None
        )
        items.append(
            {
                "date": r["contract_date"].isoformat(),
                "type": r["housing_type"],
                "deal_type": deal_type_en,
                "area_m2": area_val,
                "deposit": int(r["deposit"]),
                "monthly_rent": int(r["monthly_rent"]),
                "converted_rent": converted,
                "house_name": (r["house_name"] or "")[:50],
                # 응답 key 'build_year' 보존 (frontend lock 1).
                "build_year": r["construction_year"],
                "floor": r["floor"],
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# 메인 빌더
# ---------------------------------------------------------------------------

def build_explore_response(adong, request: Request, today: date) -> dict[str, Any]:
    """Build the explore payload from confirmed adong-scoped rent deals."""
    filters = parse_explore_filters(request)

    qs = apply_filters(RentDeal.objects.all(), adong.code, filters, today)

    return {
        "adong": {"slug": adong.slug, "code": adong.code, "name": adong.name, "gu": adong.gu},
        "filters_applied": filters,
        "kpi": compute_kpi(qs),
        "type_avg": compute_type_avg(qs, filters["deal_types"]),
        "scatter": compute_scatter(qs),
        "deposit_band": compute_deposit_band(qs),
        "monthly_trend": compute_monthly_trend(qs, filters["period"], today),
        "deals": paginate_deals(qs, filters),
    }
