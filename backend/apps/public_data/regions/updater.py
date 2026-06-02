"""Region snapshot updater for the current capston schema."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import transaction

from apps.public_data.regions.models import (
    Adong,
    AdongAdjacency,
    Gu,
    GuAdjacency,
    Ldong,
    LdongAdjacency,
    Seoul,
)
from apps.public_data.state import dataset_state, load_state, record_dataset_result, save_state


DATA_DIR = Path(__file__).resolve().parents[3] / "data"
REGION_FILES = (
    "gu_code.csv",
    "ldong_code.csv",
    "adong_code.csv",
    "gu_boundaries.geojson",
    "ldong_boundaries.geojson",
    "adong_boundaries.geojson",
)
MIN_COUNTS = {"gu": 25, "ldong": 400, "adong": 400}


@dataclass(frozen=True)
class RegionsUpdateOptions:
    dry_run: bool = True
    force: bool = False
    limit: int | None = None


def _slug(value: str) -> str:
    return value.replace(" ", "-").lower()


def _file_snapshot() -> dict[str, Any]:
    digest = hashlib.sha256()
    files = []
    for name in REGION_FILES:
        path = DATA_DIR / name
        data = path.read_bytes()
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
        files.append({"file": str(path), "file_hash": hashlib.sha256(data).hexdigest(), "file_size": len(data)})
    return {"file_hash": digest.hexdigest(), "files": files}


def _region_tables_populated() -> bool:
    return (
        Gu.objects.count() >= MIN_COUNTS["gu"]
        and Ldong.objects.count() >= MIN_COUNTS["ldong"]
        and Adong.objects.count() >= MIN_COUNTS["adong"]
        and GuAdjacency.objects.exists()
        and LdongAdjacency.objects.exists()
        and AdongAdjacency.objects.exists()
    )


def _read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _read_geojson(name: str) -> dict[str, Any]:
    with (DATA_DIR / name).open(encoding="utf-8-sig") as f:
        return json.load(f)


def _geometry(feature: dict[str, Any]) -> MultiPolygon:
    geom = GEOSGeometry(json.dumps(feature["geometry"]), srid=4326)
    if isinstance(geom, Polygon):
        return MultiPolygon(geom, srid=4326)
    if isinstance(geom, MultiPolygon):
        return geom
    raise ValueError(f"unsupported region geometry type: {geom.geom_type}")


def _area_m2(geom: MultiPolygon | None) -> Decimal | None:
    if geom is None:
        return None
    return Decimal(str(round(geom.transform(5179, clone=True).area, 4)))


def _point(geom: MultiPolygon | None):
    return geom.point_on_surface if geom is not None else None


def _validate_unique(rows: list[dict[str, str]], key: str, filename: str) -> None:
    values = [row.get(key) for row in rows]
    if any(not value for value in values):
        raise RuntimeError(f"{filename} contains blank {key}")
    if len(values) != len(set(values)):
        raise RuntimeError(f"{filename} contains duplicate {key}")


def _source_data() -> dict[str, Any]:
    gu_rows = _read_csv("gu_code.csv")
    ldong_rows = _read_csv("ldong_code.csv")
    adong_rows = _read_csv("adong_code.csv")
    gu_features = _read_geojson("gu_boundaries.geojson").get("features", [])
    ldong_features = _read_geojson("ldong_boundaries.geojson").get("features", [])
    adong_features = _read_geojson("adong_boundaries.geojson").get("features", [])

    if len(gu_rows) < MIN_COUNTS["gu"] or len(gu_features) < MIN_COUNTS["gu"]:
        raise RuntimeError("refusing region update from incomplete gu files")
    if len(ldong_rows) < MIN_COUNTS["ldong"] or len(ldong_features) < MIN_COUNTS["ldong"]:
        raise RuntimeError("refusing region update from incomplete ldong files")
    if len(adong_rows) < MIN_COUNTS["adong"] or len(adong_features) < MIN_COUNTS["adong"]:
        raise RuntimeError("refusing region update from incomplete adong files")

    _validate_unique(gu_rows, "gu_code", "gu_code.csv")
    _validate_unique(ldong_rows, "ldong_code", "ldong_code.csv")
    _validate_unique(adong_rows, "adong_code", "adong_code.csv")

    gu_codes = {row["gu_code"] for row in gu_rows}
    bad_ldong_gu = sorted({row["gu_code"] for row in ldong_rows} - gu_codes)
    bad_adong_gu = sorted({row["gu_code"] for row in adong_rows} - gu_codes)
    if bad_ldong_gu or bad_adong_gu:
        raise RuntimeError(f"region code CSV has unknown gu refs: ldong={bad_ldong_gu} adong={bad_adong_gu}")

    gu_row_by_code = {row["gu_code"]: row for row in gu_rows}
    gu_boundary_by_code = {}
    for feature in gu_features:
        props = feature.get("properties") or {}
        gu_code = str(props.get("gu_code") or "").strip()
        gu_name = str(props.get("gu_name") or props.get("name") or "").strip()
        row = gu_row_by_code.get(gu_code)
        if not row:
            raise RuntimeError(f"gu boundary has unknown gu_code={gu_code!r}")
        if gu_name and gu_name != row["gu_name"]:
            raise RuntimeError(f"gu boundary name mismatch gu_code={gu_code!r} gu_name={gu_name!r}")
        gu_boundary_by_code[gu_code] = _geometry(feature)

    ldong_boundary_by_code = {}
    for feature in ldong_features:
        props = feature.get("properties") or {}
        ldong_code = str(props.get("ldong_code") or "").strip()
        if not ldong_code:
            raise RuntimeError("ldong boundary has blank ldong_code")
        ldong_boundary_by_code[ldong_code] = _geometry(feature)

    adong_boundary_by_code = {}
    for feature in adong_features:
        props = feature.get("properties") or {}
        adong_code = str(props.get("adong_code") or "").strip()
        if not adong_code:
            raise RuntimeError("adong boundary has blank adong_code")
        adong_boundary_by_code[adong_code] = _geometry(feature)

    ldong_codes = {row["ldong_code"] for row in ldong_rows}
    adong_codes = {row["adong_code"] for row in adong_rows}
    if set(gu_boundary_by_code) != gu_codes:
        raise RuntimeError("gu boundary codes do not match gu_code.csv")
    if set(ldong_boundary_by_code) != ldong_codes:
        raise RuntimeError("ldong boundary codes do not match ldong_code.csv")
    if set(adong_boundary_by_code) != adong_codes:
        raise RuntimeError("adong boundary codes do not match adong_code.csv")

    return {
        "gu_rows": gu_rows,
        "ldong_rows": ldong_rows,
        "adong_rows": adong_rows,
        "gu_boundary_by_code": gu_boundary_by_code,
        "ldong_boundary_by_code": ldong_boundary_by_code,
        "adong_boundary_by_code": adong_boundary_by_code,
        "counts": {
            "gu": len(gu_rows),
            "ldong": len(ldong_rows),
            "adong": len(adong_rows),
            "gu_boundaries": len(gu_features),
            "ldong_boundaries": len(ldong_features),
            "adong_boundaries": len(adong_features),
        },
    }


def _adjacency_rows(model, field_a: str, field_b: str, objects: list[Any]) -> list[Any]:
    rows = []
    for idx, left in enumerate(objects):
        if not left.boundary:
            continue
        for right in objects[idx + 1 :]:
            if right.boundary and left.boundary.touches(right.boundary):
                rows.append(model(**{field_a: left, field_b: right}))
                rows.append(model(**{field_a: right, field_b: left}))
    return rows


def _replace_adjacency(model, rows: list[Any]) -> int:
    if not rows:
        raise RuntimeError(f"refusing to replace {model._meta.db_table}: computed 0 adjacency rows")
    model.objects.all().delete()
    model.objects.bulk_create(rows, ignore_conflicts=True, batch_size=1000)
    return len(rows)


def _update_regions(source: dict[str, Any], options: RegionsUpdateOptions) -> dict[str, Any]:
    checked = 0
    loaded = created = updated = 0
    deleted_missing = {"gu": 0, "ldong": 0, "adong": 0}
    adjacent_loaded = {"gu": 0, "ldong": 0, "adong": 0}

    if options.limit is not None:
        raise RuntimeError("regions updater does not support --limit because snapshot replacement must be complete")

    gu_codes = {row["gu_code"] for row in source["gu_rows"]}
    ldong_codes = {row["ldong_code"] for row in source["ldong_rows"]}
    adong_codes = {row["adong_code"] for row in source["adong_rows"]}
    gu_name_by_code = {row["gu_code"]: row["gu_name"] for row in source["gu_rows"]}
    existing_gu_codes = set(Gu.objects.filter(gu_code__in=gu_codes).values_list("gu_code", flat=True))
    existing_ldong_codes = set(Ldong.objects.filter(ldong_code__in=ldong_codes).values_list("ldong_code", flat=True))
    existing_adong_codes = set(Adong.objects.filter(adong_code__in=adong_codes).values_list("adong_code", flat=True))
    gu_objects = []
    for row in source["gu_rows"]:
        geom = source["gu_boundary_by_code"].get(row["gu_code"])
        gu_objects.append(
            Gu(
                gu_code=row["gu_code"],
                name=row["gu_name"],
                slug=_slug(row["gu_name"]),
                boundary=geom,
                location=_point(geom),
                area_m2=_area_m2(geom),
            )
        )
    ldong_objects_to_upsert = [
        Ldong(
            ldong_code=row["ldong_code"],
            name=row["ldong_name"],
            gu_id=row["gu_code"],
            slug=_slug(f"{gu_name_by_code[row['gu_code']]}-{row['ldong_name']}"),
            boundary=source["ldong_boundary_by_code"][row["ldong_code"]],
            location=_point(source["ldong_boundary_by_code"][row["ldong_code"]]),
            area_m2=_area_m2(source["ldong_boundary_by_code"][row["ldong_code"]]),
        )
        for row in source["ldong_rows"]
    ]
    adong_objects_to_upsert = [
        Adong(
            adong_code=row["adong_code"],
            name=row["adong_name"],
            gu_id=row["gu_code"],
            slug=_slug(f"{gu_name_by_code[row['gu_code']]}-{row['adong_name']}"),
            boundary=source["adong_boundary_by_code"][row["adong_code"]],
            location=_point(source["adong_boundary_by_code"][row["adong_code"]]),
            area_m2=_area_m2(source["adong_boundary_by_code"][row["adong_code"]]),
        )
        for row in source["adong_rows"]
    ]

    if options.dry_run:
        return {
            "status": "success",
            "completed": True,
            "checked": sum(source["counts"][key] for key in ("gu", "ldong", "adong")),
            "loaded": 0,
            "created": 0,
            "updated": 0,
            "deleted_missing": deleted_missing,
            "adjacent_loaded": adjacent_loaded,
            "dry_run": True,
            "source_counts": source["counts"],
        }

    with transaction.atomic():
        Gu.objects.bulk_create(
            gu_objects,
            batch_size=100,
            update_conflicts=True,
            update_fields=["name", "slug", "boundary", "location", "area_m2"],
            unique_fields=["gu_code"],
        )
        checked += len(gu_objects)
        loaded += len(gu_objects)
        created += len(gu_codes - existing_gu_codes)
        updated += len(gu_codes & existing_gu_codes)

        seoul_boundary = None
        for gu in Gu.objects.filter(gu_code__in=gu_codes).exclude(boundary__isnull=True):
            seoul_boundary = gu.boundary if seoul_boundary is None else seoul_boundary.union(gu.boundary)
        if isinstance(seoul_boundary, Polygon):
            seoul_boundary = MultiPolygon(seoul_boundary, srid=4326)
        _, was_created = Seoul.objects.update_or_create(
            code="11",
            defaults={
                "name": "서울특별시",
                "boundary": seoul_boundary,
                "location": _point(seoul_boundary),
                "area_m2": _area_m2(seoul_boundary),
            },
        )
        loaded += 1
        created += int(was_created)
        updated += int(not was_created)

        Ldong.objects.bulk_create(
            ldong_objects_to_upsert,
            batch_size=1000,
            update_conflicts=True,
            update_fields=["name", "gu", "slug", "boundary", "location", "area_m2"],
            unique_fields=["ldong_code"],
        )
        checked += len(ldong_objects_to_upsert)
        loaded += len(ldong_objects_to_upsert)
        created += len(ldong_codes - existing_ldong_codes)
        updated += len(ldong_codes & existing_ldong_codes)

        Adong.objects.bulk_create(
            adong_objects_to_upsert,
            batch_size=1000,
            update_conflicts=True,
            update_fields=["name", "gu", "slug", "boundary", "location", "area_m2"],
            unique_fields=["adong_code"],
        )
        checked += len(adong_objects_to_upsert)
        loaded += len(adong_objects_to_upsert)
        created += len(adong_codes - existing_adong_codes)
        updated += len(adong_codes & existing_adong_codes)

        gu_objects = list(Gu.objects.filter(gu_code__in=gu_codes))
        ldong_objects = list(Ldong.objects.filter(ldong_code__in=ldong_codes).exclude(boundary__isnull=True))
        adong_objects = list(Adong.objects.filter(adong_code__in=adong_codes).exclude(boundary__isnull=True))
        adjacent_loaded = {
            "gu": _replace_adjacency(GuAdjacency, _adjacency_rows(GuAdjacency, "gu_a", "gu_b", gu_objects)),
            "ldong": _replace_adjacency(
                LdongAdjacency, _adjacency_rows(LdongAdjacency, "ldong_a", "ldong_b", ldong_objects)
            ),
            "adong": _replace_adjacency(
                AdongAdjacency, _adjacency_rows(AdongAdjacency, "adong_a", "adong_b", adong_objects)
            ),
        }

        deleted_missing["adong"] = Adong.objects.exclude(adong_code__in=adong_codes).count()
        Adong.objects.exclude(adong_code__in=adong_codes).delete()
        deleted_missing["ldong"] = Ldong.objects.exclude(ldong_code__in=ldong_codes).count()
        Ldong.objects.exclude(ldong_code__in=ldong_codes).delete()
        deleted_missing["gu"] = Gu.objects.exclude(gu_code__in=gu_codes).count()
        Gu.objects.exclude(gu_code__in=gu_codes).delete()
        Seoul.objects.exclude(code="11").delete()

    return {
        "status": "success",
        "completed": True,
        "checked": checked,
        "loaded": loaded,
        "created": created,
        "updated": updated,
        "deleted_missing": deleted_missing,
        "adjacent_loaded": adjacent_loaded,
        "dry_run": False,
        "source_counts": source["counts"],
    }


def update_regions(options: RegionsUpdateOptions) -> dict[str, Any]:
    snapshot = _file_snapshot()
    previous_snapshot = dataset_state("regions").get("snapshot", {})
    if (
        not options.force
        and not options.dry_run
        and previous_snapshot.get("file_hash") == snapshot["file_hash"]
        and _region_tables_populated()
    ):
        return {
            "status": "success",
            "completed": True,
            "skipped_write": True,
            "reason": "file_hash_unchanged",
            "dry_run": options.dry_run,
            "files": snapshot,
            "loaded": 0,
            "deleted_missing": {"gu": 0, "ldong": 0, "adong": 0},
            "adjacent_loaded": {"gu": 0, "ldong": 0, "adong": 0},
        }

    source = _source_data()
    snapshot["counts"] = source["counts"]

    result = _update_regions(source, options)
    result["files"] = snapshot
    return result


def update(options: RegionsUpdateOptions) -> dict[str, Any]:
    result: dict[str, Any] = {
        "dataset": "regions",
        "dry_run": options.dry_run,
        "regions": None,
    }
    try:
        result["regions"] = update_regions(options)
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if not options.dry_run:
            record_dataset_result("regions", result)
        raise

    if not options.dry_run:
        record_dataset_result("regions", result)
        if (
            result["regions"]
            and result["regions"].get("completed")
            and not result["regions"].get("skipped_write")
        ):
            state = load_state()
            regions_state = state.setdefault("datasets", {}).setdefault("regions", {})
            regions_state["snapshot"] = result["regions"]["files"] | {
                "last_success_date": None,
                "loaded": result["regions"]["loaded"],
                "adjacent_loaded": result["regions"]["adjacent_loaded"],
                "deleted_missing": result["regions"]["deleted_missing"],
            }
            save_state(state)
    return result
