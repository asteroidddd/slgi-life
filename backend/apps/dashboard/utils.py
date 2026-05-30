from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from apps.public_data.regions.models import Adong, Ldong


@dataclass(frozen=True)
class DashboardRegion:
    region_type: str
    code: str
    slug: str
    gu_code: str
    gu_name: str
    dong_name: str
    area_km2: float | None
    bbox: tuple[float, float, float, float] | None
    obj: Any

    @property
    def rent_field(self) -> str:
        return "adong_code" if self.region_type == "adong" else "ldong_code"

    @property
    def amenity_link_table(self) -> str:
        return "amenity_adong" if self.region_type == "adong" else "amenity_ldong"

    @property
    def amenity_link_column(self) -> str:
        return "adong_code" if self.region_type == "adong" else "ldong_code"


def _area_km2(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value) / 1_000_000.0
    except (TypeError, ValueError):
        return None


def _bbox(boundary: Any) -> tuple[float, float, float, float] | None:
    if not boundary:
        return None
    try:
        return tuple(float(item) for item in boundary.extent)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


def resolve_region(request: Request) -> DashboardRegion:
    region_type = request.query_params.get("region_type") or request.query_params.get("type")
    slug = request.query_params.get("slug")
    if not region_type:
        raise ValidationError({"region_type": "region_type is required: adong or ldong."})
    if not slug:
        raise ValidationError({"slug": "slug is required."})

    if region_type == "adong":
        region = get_object_or_404(Adong.objects.select_related("gu"), slug=slug)
        code = region.adong_code
    elif region_type == "ldong":
        region = get_object_or_404(Ldong.objects.select_related("gu"), slug=slug)
        code = region.ldong_code
    else:
        raise ValidationError({"region_type": "region_type must be adong or ldong."})

    return DashboardRegion(
        region_type=region_type,
        code=code,
        slug=region.slug or "",
        gu_code=region.gu_id,
        gu_name=region.gu.name,
        dong_name=region.name,
        area_km2=_area_km2(region.area_m2),
        bbox=_bbox(region.boundary),
        obj=region,
    )


def region_payload(region: DashboardRegion) -> dict[str, Any]:
    return {
        "type": region.region_type,
        "code": region.code,
        "slug": region.slug,
        "gu_code": region.gu_code,
        "gu_name": region.gu_name,
        "dong_name": region.dong_name,
        "area_km2": region.area_km2,
        "bbox": list(region.bbox) if region.bbox else None,
    }


def parse_months(request: Request, *, default: int = 6, minimum: int = 1, maximum: int = 24) -> int:
    raw = request.query_params.get("months")
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValidationError({"months": "months must be an integer."}) from exc
    if value < minimum or value > maximum:
        raise ValidationError({"months": f"months must be between {minimum} and {maximum}."})
    return value


def parse_limit(request: Request, *, default: int = 100, maximum: int = 500) -> int:
    raw = request.query_params.get("limit")
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValidationError({"limit": "limit must be an integer."}) from exc
    return max(1, min(value, maximum))


def tone_from_delta(delta_ratio: float | None, *, higher_is_bad: bool = False, threshold: float = 0.1) -> str:
    if delta_ratio is None or abs(delta_ratio) < threshold:
        return "info"
    high = delta_ratio > 0
    if higher_is_bad:
        return "bad" if high else "good"
    return "good" if high else "bad"


def pct_delta(value: float | None, base: float | None) -> float | None:
    if value is None or base in (None, 0):
        return None
    return (value - base) / base


def fmt_delta(delta_ratio: float | None, *, base_label: str) -> str:
    if delta_ratio is None:
        return f"{base_label} 비교값 없음"
    sign = "+" if delta_ratio >= 0 else ""
    return f"{base_label} 대비 {sign}{delta_ratio * 100:.1f}%"


def metric(key: str, label: str, value: Any, unit: str = "", *, tone: str = "info", badge: str = "", description: str = "") -> dict[str, Any]:
    return {"key": key, "label": label, "value": value, "unit": unit, "tone": tone, "badge": badge, "description": description}


def quicktake(label: str, tone: str = "info") -> dict[str, str]:
    return {"label": label, "tone": tone}
