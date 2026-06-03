from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from django.contrib.gis.geos import Point
from django.db import transaction

from apps.public_data.bus.models import BusStop
from apps.public_data.library.models import Library
from apps.public_data.medical.models import MedicalFacility
from apps.public_data.park.models import Park
from apps.public_data.regions.models import Adong, Ldong
from apps.public_data.store.models import DaisoStore, Store
from apps.public_data.subway.models import SubwayStation
from apps.service.amenities.models import Amenity, AmenityAdong, AmenityLdong


BATCH_SIZE = 5000
MEDICAL_STORE_CATEGORY_CODES = {"G21501"}
MEDICAL_STORE_MAIN_CATEGORY_CODES = {"Q1"}
MEDICAL_AMENITY_EXCLUDED_TYPES = {"\uae30\ud0c0", "\uae30\ud0c0(\uad6c\uae09\ucc28)", "\uc694\uc591\ubcd1\uc6d0", "\uc870\uc0b0\uc6d0"}
MEDICAL_AMENITY_CATEGORY_BY_TYPE = {
    "\uc57d\uad6d": "pharmacy",
    "\uce58\uacfc\ubcd1\uc6d0": "dental",
    "\uce58\uacfc\uc758\uc6d0": "dental",
}

OLIVEYOUNG_KEYWORDS = ("\uc62c\ub9ac\ube0c\uc601", "oliveyoung")

STORE_CATEGORY_BY_SUBCATEGORY_CODE = {
    "G20405": "convenience",
    "G20404": "etc",
    "I21201": "cafe",
    "S20901": "etc",
    "S20902": "laundry",
    "R10307": "gym",
    "G21301": "etc",
    "G21302": "etc",
    "R10202": "study_cafe",
}
STORE_CATEGORY_BY_MIDDLE_CATEGORY_CODE = {
    "I211": "etc",
    "S207": "etc",
}
RESTAURANT_EXCLUDED_SUBCATEGORY_CODES = {"I21201", "I20701"}


@dataclass(frozen=True)
class AmenitySourceRow:
    category: str
    name: str
    location: Point
    source_table: str
    source_id: str
    adong_ids: tuple[str, ...] = ()
    ldong_ids: tuple[str, ...] = ()


def _chunks(rows: Iterable[AmenitySourceRow], size: int) -> Iterator[list[AmenitySourceRow]]:
    batch: list[AmenitySourceRow] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _clean_name(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return text[:200] if text else fallback


def _medical_category(facility_type: str) -> str | None:
    if facility_type in MEDICAL_AMENITY_EXCLUDED_TYPES:
        return None
    return MEDICAL_AMENITY_CATEGORY_BY_TYPE.get(facility_type, "hospital")

def _is_medical_store_category(category_id: str | None, category_main_category_code: str | None) -> bool:
    if category_id and (category_id in MEDICAL_STORE_CATEGORY_CODES or category_id.startswith("Q1")):
        return True
    return category_main_category_code in MEDICAL_STORE_MAIN_CATEGORY_CODES


def _is_oliveyoung(name: Any) -> bool:
    text = str(name or "").lower()
    return any(keyword.lower() in text for keyword in OLIVEYOUNG_KEYWORDS)


def _store_category_from_values(
    *,
    name: Any,
    category_id: str | None,
    category_middle_category_code: str | None,
    category_main_category_code: str | None,
) -> str | None:
    if _is_medical_store_category(category_id, category_main_category_code):
        return None
    if _is_oliveyoung(name):
        return "oliveyoung"
    if category_id in STORE_CATEGORY_BY_SUBCATEGORY_CODE:
        return STORE_CATEGORY_BY_SUBCATEGORY_CODE[category_id]
    if category_middle_category_code in STORE_CATEGORY_BY_MIDDLE_CATEGORY_CODE:
        return STORE_CATEGORY_BY_MIDDLE_CATEGORY_CODE[category_middle_category_code]
    if (
        category_main_category_code == "I2"
        and category_id not in RESTAURANT_EXCLUDED_SUBCATEGORY_CODES
        and category_middle_category_code != "I211"
    ):
        return "restaurant"
    return "etc"


def _iter_store_rows() -> Iterator[AmenitySourceRow]:
    qs = (
        Store.objects.filter(location__isnull=False)
        .exclude(category_id__in=MEDICAL_STORE_CATEGORY_CODES)
        .exclude(category__main_category_code__in=MEDICAL_STORE_MAIN_CATEGORY_CODES)
        .values_list(
            "id",
            "name",
            "category_id",
            "category__middle_category_code",
            "category__main_category_code",
            "location",
            "adong_id",
            "ldong_id",
        )
        .iterator(chunk_size=BATCH_SIZE)
    )
    for (
        store_id,
        name,
        category_id,
        category_middle_category_code,
        category_main_category_code,
        location,
        adong_id,
        ldong_id,
    ) in qs:
        category = _store_category_from_values(
            name=name,
            category_id=category_id,
            category_middle_category_code=category_middle_category_code,
            category_main_category_code=category_main_category_code,
        )
        if not category:
            continue
        yield AmenitySourceRow(
            category=category,
            name=_clean_name(name, store_id),
            location=location,
            source_table="store",
            source_id=str(store_id),
            adong_ids=(adong_id,) if adong_id else (),
            ldong_ids=(ldong_id,) if ldong_id else (),
        )


def _region_ids_for_point(point: Point) -> tuple[tuple[str, ...], tuple[str, ...]]:
    adong_id = (
        Adong.objects.filter(boundary__covers=point)
        .order_by("area_m2")
        .values_list("adong_code", flat=True)
        .first()
    )
    ldong_id = (
        Ldong.objects.filter(boundary__covers=point)
        .order_by("area_m2")
        .values_list("ldong_code", flat=True)
        .first()
    )
    return ((adong_id,) if adong_id else (), (ldong_id,) if ldong_id else ())


def _iter_daiso_rows() -> Iterator[AmenitySourceRow]:
    qs = DaisoStore.objects.filter(location__isnull=False).values_list("id", "name", "location")
    for daiso_id, name, location in qs.iterator(chunk_size=BATCH_SIZE):
        adong_ids, ldong_ids = _region_ids_for_point(location)
        yield AmenitySourceRow(
            category="daiso",
            name=_clean_name(name, daiso_id),
            location=location,
            source_table="daiso_store",
            source_id=str(daiso_id),
            adong_ids=adong_ids,
            ldong_ids=ldong_ids,
        )


def _iter_medical_rows() -> Iterator[AmenitySourceRow]:
    qs = MedicalFacility.objects.filter(location__isnull=False).values_list(
        "hpid",
        "type",
        "name",
        "location",
        "adong_id",
        "ldong_id",
    )
    for hpid, facility_type, name, location, adong_id, ldong_id in qs.iterator(chunk_size=BATCH_SIZE):
        category = _medical_category(facility_type)
        if not category:
            continue
        yield AmenitySourceRow(
            category=category,
            name=_clean_name(name, hpid),
            location=location,
            source_table="medical_facility",
            source_id=str(hpid),
            adong_ids=(adong_id,) if adong_id else (),
            ldong_ids=(ldong_id,) if ldong_id else (),
        )

def _iter_park_rows() -> Iterator[AmenitySourceRow]:
    adongs_by_park: dict[str, list[str]] = {}
    ldongs_by_park: dict[str, list[str]] = {}
    for park_id, adong_id in Park.objects.filter(park_dongs__isnull=False).values_list("id", "park_dongs__adong_id"):
        adongs_by_park.setdefault(park_id, []).append(adong_id)
    for park_id, ldong_id in Park.objects.filter(park_ldongs__isnull=False).values_list("id", "park_ldongs__ldong_id"):
        ldongs_by_park.setdefault(park_id, []).append(ldong_id)

    for park_id, name, category, location in Park.objects.filter(location__isnull=False).values_list(
        "id",
        "name",
        "category",
        "location",
    ).iterator(chunk_size=BATCH_SIZE):
        yield AmenitySourceRow(
            category="park",
            name=_clean_name(" ".join(part for part in (str(name or "").strip(), str(category or "").strip()) if part), park_id),
            location=location,
            source_table="park",
            source_id=str(park_id),
            adong_ids=tuple(adongs_by_park.get(park_id, ())),
            ldong_ids=tuple(ldongs_by_park.get(park_id, ())),
        )


def _iter_library_rows() -> Iterator[AmenitySourceRow]:
    qs = Library.objects.filter(location__isnull=False).values_list("id", "name", "location", "adong_id", "ldong_id")
    for library_id, name, location, adong_id, ldong_id in qs.iterator(chunk_size=BATCH_SIZE):
        yield AmenitySourceRow("library", _clean_name(name, library_id), location, "library", str(library_id), (adong_id,) if adong_id else (), (ldong_id,) if ldong_id else ())


def _iter_subway_rows() -> Iterator[AmenitySourceRow]:
    qs = SubwayStation.objects.filter(location__isnull=False).values_list("id", "name", "line", "location", "adong_id", "ldong_id")
    for station_id, name, line, location, adong_id, ldong_id in qs.iterator(chunk_size=BATCH_SIZE):
        yield AmenitySourceRow("subway_station", _clean_name(f"{name}({line})", station_id), location, "subway_station", str(station_id), (adong_id,) if adong_id else (), (ldong_id,) if ldong_id else ())


def _iter_bus_rows() -> Iterator[AmenitySourceRow]:
    qs = BusStop.objects.filter(location__isnull=False).values_list("id", "name", "location", "adong_id", "ldong_id")
    for stop_id, name, location, adong_id, ldong_id in qs.iterator(chunk_size=BATCH_SIZE):
        yield AmenitySourceRow("bus_stop", _clean_name(name, stop_id), location, "bus_stop", str(stop_id), (adong_id,) if adong_id else (), (ldong_id,) if ldong_id else ())


def iter_source_rows() -> Iterator[AmenitySourceRow]:
    yield from _iter_store_rows()
    yield from _iter_daiso_rows()
    yield from _iter_medical_rows()
    yield from _iter_park_rows()
    yield from _iter_library_rows()
    yield from _iter_subway_rows()
    yield from _iter_bus_rows()


def rebuild_amenities(*, dry_run: bool = False, batch_size: int = BATCH_SIZE) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "dry_run": dry_run,
        "created": 0,
        "links_adong": 0,
        "links_ldong": 0,
        "by_source": {},
        "by_category": {},
    }

    if dry_run:
        for row in iter_source_rows():
            stats["created"] += 1
            stats["by_source"][row.source_table] = stats["by_source"].get(row.source_table, 0) + 1
            stats["by_category"][row.category] = stats["by_category"].get(row.category, 0) + 1
            stats["links_adong"] += len(row.adong_ids)
            stats["links_ldong"] += len(row.ldong_ids)
        return stats

    with transaction.atomic():
        AmenityAdong.objects.all().delete()
        AmenityLdong.objects.all().delete()
        Amenity.objects.all().delete()

        for batch in _chunks(iter_source_rows(), batch_size):
            amenities = [
                Amenity(
                    category=row.category,
                    name=row.name,
                    location=row.location,
                    source_table=row.source_table,
                    source_id=row.source_id,
                )
                for row in batch
            ]
            created = Amenity.objects.bulk_create(amenities, batch_size=batch_size)
            key_to_id = {(amenity.source_table, amenity.source_id): amenity.id for amenity in created}
            if any(amenity_id is None for amenity_id in key_to_id.values()):
                source_ids = [row.source_id for row in batch]
                key_to_id = {
                    (amenity.source_table, amenity.source_id): amenity.id
                    for amenity in Amenity.objects.filter(source_id__in=source_ids)
                }

            adong_links: list[AmenityAdong] = []
            ldong_links: list[AmenityLdong] = []
            for row in batch:
                amenity_id = key_to_id[(row.source_table, row.source_id)]
                adong_links.extend(AmenityAdong(amenity_id=amenity_id, adong_id=adong_id) for adong_id in row.adong_ids)
                ldong_links.extend(AmenityLdong(amenity_id=amenity_id, ldong_id=ldong_id) for ldong_id in row.ldong_ids)
                stats["by_source"][row.source_table] = stats["by_source"].get(row.source_table, 0) + 1
                stats["by_category"][row.category] = stats["by_category"].get(row.category, 0) + 1

            AmenityAdong.objects.bulk_create(adong_links, batch_size=batch_size, ignore_conflicts=True)
            AmenityLdong.objects.bulk_create(ldong_links, batch_size=batch_size, ignore_conflicts=True)
            stats["created"] += len(batch)
            stats["links_adong"] += len(adong_links)
            stats["links_ldong"] += len(ldong_links)

    return stats
