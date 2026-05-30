from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.dashboard.cache.bulk import CACHE_SOURCE_VERSION, build_dashboard_payloads
from apps.dashboard.cache.models import DashboardAdongCache, DashboardLdongCache


@dataclass(frozen=True)
class CacheUpdateResult:
    region_type: str
    code: str
    slug: str
    ok: bool
    error: str = ""


def _cache_model(region_type: str):
    if region_type == "adong":
        return DashboardAdongCache, "adong_id", "adong"
    if region_type == "ldong":
        return DashboardLdongCache, "ldong_id", "ldong"
    raise ValueError(f"Unsupported dashboard cache region_type: {region_type}")


def _build_objects(region_type: str, payloads: dict[str, dict], computed_at):
    model, id_field, _unique_field = _cache_model(region_type)
    objects = []
    for code, payload in payloads.items():
        full_payload = {
            "region": payload["region"],
            "intro": payload["intro"],
            "rent_summary": payload["rent_summary"],
            "transit_summary": payload["transit_summary"],
            "infra_summary": payload["infra_summary"],
            "safety_summary": payload["safety_summary"],
            "source_version": CACHE_SOURCE_VERSION,
            "computed_at": computed_at.isoformat(),
        }
        objects.append(
            model(
                **{id_field: code},
                region_payload=payload["region"],
                intro=payload["intro"],
                rent_summary=payload["rent_summary"],
                transit_summary=payload["transit_summary"],
                infra_summary=payload["infra_summary"],
                safety_summary=payload["safety_summary"],
                dashboard_payload=full_payload,
                source_version=CACHE_SOURCE_VERSION,
                computed_at=computed_at,
            )
        )
    return objects


def update_region_type(
    region_type: str,
    *,
    limit: int | None = None,
    offset: int = 0,
    truncate: bool = False,
) -> list[CacheUpdateResult]:
    model, _id_field, unique_field = _cache_model(region_type)
    computed_at = timezone.now()
    payloads = build_dashboard_payloads(region_type, limit=limit, offset=offset)
    objects = _build_objects(region_type, payloads, computed_at)
    with transaction.atomic():
        if truncate:
            model.objects.all().delete()
        if objects:
            model.objects.bulk_create(
                objects,
                batch_size=100,
                update_conflicts=True,
                update_fields=[
                    "region_payload",
                    "intro",
                    "rent_summary",
                    "transit_summary",
                    "infra_summary",
                    "safety_summary",
                    "dashboard_payload",
                    "source_version",
                    "computed_at",
                ],
                unique_fields=[unique_field],
            )

    return [
        CacheUpdateResult(
            region_type=region_type,
            code=code,
            slug=payload["region"].get("slug") or "",
            ok=True,
        )
        for code, payload in payloads.items()
    ]


def update_all(
    *,
    region_type: str = "all",
    limit: int | None = None,
    offset: int = 0,
    truncate: bool = False,
) -> list[CacheUpdateResult]:
    region_types = ["adong", "ldong"] if region_type == "all" else [region_type]
    results: list[CacheUpdateResult] = []
    for item in region_types:
        item_limit = limit if region_type != "all" else None
        item_offset = offset if region_type != "all" else 0
        results.extend(
            update_region_type(
                item,
                limit=item_limit,
                offset=item_offset,
                truncate=truncate,
            )
        )
    return results
