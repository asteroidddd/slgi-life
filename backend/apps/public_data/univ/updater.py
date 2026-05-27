"""University public-data updater for the current capston schema."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import transaction

from apps.public_data.regions.models import Adong, Ldong
from apps.public_data.state import dataset_state, load_state, record_dataset_result, save_state
from apps.public_data.univ.models import Univ, UnivAdong, UnivLdong


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "university_boundaries.geojson"
MIN_FEATURE_COUNT = 50


@dataclass(frozen=True)
class UnivUpdateOptions:
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
    raise ValueError(f"unsupported university geometry type: {geom.geom_type}")


def _build_records(features: list[dict[str, Any]], options: UnivUpdateOptions) -> dict[str, Any]:
    ldongs = list(Ldong.objects.exclude(boundary__isnull=True))
    adongs = list(Adong.objects.exclude(boundary__isnull=True))
    if not ldongs or not adongs:
        raise RuntimeError("region boundaries are required before updating universities")

    records: list[dict[str, Any]] = []
    ldong_links: list[tuple[str, str]] = []
    adong_links: list[tuple[str, str]] = []
    source_ids: set[str] = set()
    checked = skipped = 0
    skip_reasons = {"bad_geometry": 0, "missing_required": 0}

    for feature in features:
        if options.limit is not None and checked >= options.limit:
            break
        checked += 1
        props = feature.get("properties") or {}
        try:
            univ_id = str(props.get("id") or "").strip()
            name = str(props.get("name") or "").strip()
            school_type = str(props.get("school_type") or "").strip()
            geom = _geometry(feature)
        except (KeyError, TypeError, ValueError):
            skipped += 1
            skip_reasons["bad_geometry"] += 1
            continue
        if not (univ_id and name and school_type):
            skipped += 1
            skip_reasons["missing_required"] += 1
            continue

        univ_id = univ_id[:5]
        source_ids.add(univ_id)
        records.append(
            {
                "id": univ_id,
                "defaults": {
                    "name": name[:200],
                    "school_type": school_type[:20],
                    "boundary": geom,
                    "location": geom.point_on_surface,
                },
            }
        )
        for ldong in ldongs:
            if geom.intersects(ldong.boundary):
                ldong_links.append((univ_id, ldong.ldong_code))
        for adong in adongs:
            if geom.intersects(adong.boundary):
                adong_links.append((univ_id, adong.adong_code))

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


def update_univ(options: UnivUpdateOptions) -> dict[str, Any]:
    meta = _file_meta(DATA_PATH)
    features = _read_geojson(DATA_PATH).get("features", [])
    meta["feature_count"] = len(features)
    if len(features) < MIN_FEATURE_COUNT:
        raise RuntimeError(f"refusing university update from incomplete file: {len(features)} features")

    previous_snapshot = dataset_state("univ").get("snapshot", {})
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
            "relations": {"univ_ldong": 0, "univ_adong": 0},
            "deleted_missing": 0,
        }

    built = _build_records(features, options)
    completed = bool(built["completed"] and built["records"])
    if completed and (not built["ldong_links"] or not built["adong_links"]):
        raise RuntimeError("refusing to replace university relations: computed empty relation set")

    loaded = created = updated = deleted_missing = 0
    if not options.dry_run:
        with transaction.atomic():
            univ_by_id: dict[str, Univ] = {}
            for record in built["records"]:
                univ, was_created = Univ.objects.update_or_create(
                    id=record["id"],
                    defaults=record["defaults"],
                )
                univ_by_id[record["id"]] = univ
                loaded += 1
                created += int(was_created)
                updated += int(not was_created)

            if completed:
                UnivLdong.objects.all().delete()
                UnivAdong.objects.all().delete()
                UnivLdong.objects.bulk_create(
                    [
                        UnivLdong(univ=univ_by_id[univ_id], ldong_id=ldong_code)
                        for univ_id, ldong_code in built["ldong_links"]
                        if univ_id in univ_by_id
                    ],
                    ignore_conflicts=True,
                    batch_size=1000,
                )
                UnivAdong.objects.bulk_create(
                    [
                        UnivAdong(univ=univ_by_id[univ_id], adong_id=adong_code)
                        for univ_id, adong_code in built["adong_links"]
                        if univ_id in univ_by_id
                    ],
                    ignore_conflicts=True,
                    batch_size=1000,
                )
                missing_queryset = Univ.objects.exclude(id__in=built["source_ids"])
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
            "univ_ldong": len(built["ldong_links"]) if completed else 0,
            "univ_adong": len(built["adong_links"]) if completed else 0,
        },
        "skip_reasons": built["skip_reasons"],
    }


def update(options: UnivUpdateOptions) -> dict[str, Any]:
    result: dict[str, Any] = {
        "dataset": "univ",
        "dry_run": options.dry_run,
        "univ": None,
    }
    try:
        result["univ"] = update_univ(options)
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if not options.dry_run:
            record_dataset_result("univ", result)
        raise

    if not options.dry_run:
        record_dataset_result("univ", result)
        if result["univ"] and result["univ"].get("completed"):
            state = load_state()
            univ_state = state.setdefault("datasets", {}).setdefault("univ", {})
            univ_state["snapshot"] = result["univ"]["files"] | {
                "loaded": result["univ"]["loaded"],
                "deleted_missing": result["univ"]["deleted_missing"],
                "relations": result["univ"]["relations"],
            }
            save_state(state)
    return result
