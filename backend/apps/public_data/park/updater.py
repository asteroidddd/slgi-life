"""Park public-data updater for the current capston schema."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import transaction

from apps.public_data.park.models import Park, ParkAdong, ParkLdong
from apps.public_data.regions.models import Adong, Ldong
from apps.public_data.state import dataset_state, load_state, record_dataset_result, save_state


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "park_boundaries.geojson"
MIN_FEATURE_COUNT = 1000


@dataclass(frozen=True)
class ParksUpdateOptions:
    dry_run: bool = True
    force: bool = False
    limit: int | None = None


def _file_meta(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "file": str(path),
        "file_hash": hashlib.sha256(data).hexdigest(),
        "file_size": len(data),
    }


def _read_geojson(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def _geometry(feature: dict[str, Any]) -> MultiPolygon:
    geom = GEOSGeometry(json.dumps(feature["geometry"]), srid=4326)
    if isinstance(geom, Polygon):
        return MultiPolygon(geom, srid=4326)
    if isinstance(geom, MultiPolygon):
        return geom
    raise ValueError(f"unsupported park geometry type: {geom.geom_type}")


def _area_m2(geom: MultiPolygon) -> Decimal:
    return Decimal(str(round(geom.transform(5179, clone=True).area, 4)))


def _label(props: dict[str, Any]) -> str:
    return str(props.get("LABEL") or props.get("ID") or "").strip()


def _category(label: str, props: dict[str, Any]) -> str:
    match = re.match(r"\s*([^()]+)", label)
    if match and match.group(1).strip():
        return match.group(1).strip()[:50]
    return str(props.get("CODE") or props.get("ENT_NAME") or "공원")[:50]


def _park_id(props: dict[str, Any]) -> str:
    value = str(props.get("ID") or "").strip()
    if not value:
        raise ValueError("missing park ID")
    return value[:50]


def _build_records(features: list[dict[str, Any]], options: ParksUpdateOptions) -> dict[str, Any]:
    ldongs = list(Ldong.objects.exclude(boundary__isnull=True))
    adongs = list(Adong.objects.exclude(boundary__isnull=True))
    if not ldongs or not adongs:
        raise RuntimeError("region boundaries are required before updating parks")

    records: list[dict[str, Any]] = []
    ldong_links: list[tuple[str, str]] = []
    adong_links: list[tuple[str, str]] = []
    source_ids: set[str] = set()
    skip_reasons = {"bad_geometry": 0, "missing_required": 0}
    checked = skipped = 0

    for feature in features:
        if options.limit is not None and checked >= options.limit:
            break
        checked += 1
        props = feature.get("properties") or {}
        try:
            park_id = _park_id(props)
            source_ids.add(park_id)
            name = _label(props)
            geom = _geometry(feature)
        except (KeyError, TypeError, ValueError):
            skipped += 1
            skip_reasons["bad_geometry"] += 1
            continue
        if not name:
            skipped += 1
            skip_reasons["missing_required"] += 1
            continue

        records.append(
            {
                "id": park_id,
                "defaults": {
                    "name": name[:200],
                    "category": _category(name, props),
                    "area_m2": _area_m2(geom),
                    "boundary": geom,
                    "location": geom.point_on_surface,
                },
            }
        )
        for ldong in ldongs:
            if geom.intersects(ldong.boundary):
                ldong_links.append((park_id, ldong.ldong_code))
        for adong in adongs:
            if geom.intersects(adong.boundary):
                adong_links.append((park_id, adong.adong_code))

    return {
        "checked": checked,
        "skipped": skipped,
        "records": records,
        "ldong_links": ldong_links,
        "adong_links": adong_links,
        "source_ids": source_ids,
        "skip_reasons": skip_reasons,
        "completed": options.limit is None or checked >= len(features),
    }


def update_parks(options: ParksUpdateOptions) -> dict[str, Any]:
    meta = _file_meta(DATA_PATH)
    features = _read_geojson(DATA_PATH).get("features", [])
    meta["feature_count"] = len(features)
    if len(features) < MIN_FEATURE_COUNT:
        raise RuntimeError(f"refusing park update from incomplete file: {len(features)} features")

    previous_snapshot = dataset_state("parks").get("snapshot", {})
    if (
        not options.force
        and not options.dry_run
        and previous_snapshot.get("file_hash") == meta["file_hash"]
    ):
        return {
            "status": "success",
            "completed": True,
            "skipped_write": True,
            "reason": "file_hash_unchanged",
            "dry_run": options.dry_run,
            "files": meta,
            "loaded": 0,
            "relations": {"park_ldong": 0, "park_adong": 0},
            "deleted_missing": 0,
        }

    built = _build_records(features, options)
    completed = bool(built["completed"] and built["records"])
    if completed and (not built["ldong_links"] or not built["adong_links"]):
        raise RuntimeError("refusing to replace park relations: computed empty relation set")

    loaded = created = updated = deleted_missing = 0
    if not options.dry_run:
        with transaction.atomic():
            park_by_id: dict[str, Park] = {}
            for record in built["records"]:
                park, was_created = Park.objects.update_or_create(
                    id=record["id"],
                    defaults=record["defaults"],
                )
                park_by_id[record["id"]] = park
                loaded += 1
                if was_created:
                    created += 1
                else:
                    updated += 1

            if completed:
                ParkLdong.objects.all().delete()
                ParkAdong.objects.all().delete()
                ParkLdong.objects.bulk_create(
                    [
                        ParkLdong(park=park_by_id[park_id], ldong_id=ldong_code)
                        for park_id, ldong_code in built["ldong_links"]
                        if park_id in park_by_id
                    ],
                    ignore_conflicts=True,
                    batch_size=1000,
                )
                ParkAdong.objects.bulk_create(
                    [
                        ParkAdong(park=park_by_id[park_id], adong_id=adong_code)
                        for park_id, adong_code in built["adong_links"]
                        if park_id in park_by_id
                    ],
                    ignore_conflicts=True,
                    batch_size=1000,
                )
                missing_queryset = Park.objects.exclude(id__in=built["source_ids"])
                deleted_missing = missing_queryset.count()
                missing_queryset.delete()

    return {
        "status": "success" if completed else "partial",
        "completed": completed,
        "checked": built["checked"],
        "loaded": loaded if not options.dry_run else len(built["records"]),
        "created": created,
        "updated": updated,
        "skipped": built["skipped"],
        "deleted_missing": deleted_missing,
        "dry_run": options.dry_run,
        "files": meta,
        "relations": {
            "park_ldong": len(built["ldong_links"]) if completed else 0,
            "park_adong": len(built["adong_links"]) if completed else 0,
        },
        "skip_reasons": built["skip_reasons"],
    }


def update(options: ParksUpdateOptions) -> dict[str, Any]:
    result: dict[str, Any] = {
        "dataset": "parks",
        "dry_run": options.dry_run,
        "parks": None,
    }
    try:
        result["parks"] = update_parks(options)
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if not options.dry_run:
            record_dataset_result("parks", result)
        raise

    if not options.dry_run:
        record_dataset_result("parks", result)
        if (
            result["parks"]
            and result["parks"].get("completed")
            and not result["parks"].get("skipped_write")
        ):
            state = load_state()
            parks_state = state.setdefault("datasets", {}).setdefault("parks", {})
            parks_state["snapshot"] = result["parks"]["files"] | {
                "last_success_date": None,
                "loaded": result["parks"]["loaded"],
                "relations": result["parks"]["relations"],
                "deleted_missing": result["parks"]["deleted_missing"],
            }
            save_state(state)
    return result
