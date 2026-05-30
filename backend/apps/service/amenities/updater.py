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
from apps.public_data.store.models import Store
from apps.public_data.subway.models import SubwayStation
from apps.public_data.univ.models import Univ
from apps.service.amenities.models import Amenity, AmenityAdong, AmenityLdong


BATCH_SIZE = 5000
MEDICAL_STORE_CATEGORY_CODES = {
    "G21501",
    "Q10101", "Q10102", "Q10103", "Q10104",
    "Q10201", "Q10202", "Q10203", "Q10204", "Q10205", "Q10206",
    "Q10207", "Q10208", "Q10209", "Q10210", "Q10211",
}
MEDICAL_AMENITY_EXCLUDED_TYPES = {"\uae30\ud0c0", "\uae30\ud0c0(\uad6c\uae09\ucc28)", "\uc694\uc591\ubcd1\uc6d0", "\uc870\uc0b0\uc6d0"}
MEDICAL_AMENITY_CATEGORY_BY_TYPE = {
    "\uc57d\uad6d": "pharmacy",
    "\uce58\uacfc\ubcd1\uc6d0": "dental",
    "\uce58\uacfc\uc758\uc6d0": "dental",
}

STORE_MEDICAL_AMENITY_CATEGORIES = {"hospital", "dental", "pharmacy"}

STORE_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("convenience", ("\ud3b8\uc758\uc810", "\uc288\ud37c", "\uc288\ud37c\ub9c8\ucf13", "24\uc2dc")),
    ("mart", ("\ub9c8\ud2b8", "\ub300\ud615\ub9c8\ud2b8", "\uc2dd\uc790\uc7ac", "\ud560\uc778\uc810")),
    ("restaurant", ("\uc74c\uc2dd", "\ud55c\uc2dd", "\uc911\uc2dd", "\uc77c\uc2dd", "\ubd84\uc2dd", "\uc591\uc2dd", "\uc2dd\ub2f9", "\ub808\uc2a4\ud1a0\ub791")),
    ("cafe", ("\ucee4\ud53c", "\uce74\ud398", "\ub2e4\ubc29", "\uc74c\ub8cc")),
    ("nightlife", ("\uc8fc\uc810", "\ud638\ud504", "\ub9e5\uc8fc", "\uc18c\uc8fc", "\ubc14 ", "bar", "\ud3ec\ucc28", "\uc220\uc9d1")),
    ("hospital", ("\ubcd1\uc6d0", "\uc758\uc6d0", "\ud55c\uc758\uc6d0", "\uc758\ub8cc")),
    ("dental", ("\uce58\uacfc",)),
    ("pharmacy", ("\uc57d\uad6d",)),
    ("laundry", ("\uc138\ud0c1", "\ube68\ub798\ubc29", "\ud06c\ub9ac\ub2dd")),
    ("beauty", ("\ubbf8\uc6a9", "\ud5e4\uc5b4", "\ub124\uc77c", "\ud53c\ubd80", "\ubdf0\ud2f0")),
    ("oliveyoung", ("\uc62c\ub9ac\ube0c\uc601", "oliveyoung")),
    ("gym", ("\ud5ec\uc2a4", "\uccb4\uc721", "\ud53c\ud2b8\ub2c8\uc2a4", "\uc694\uac00", "\ud544\ub77c\ud14c\uc2a4", "\uc6b4\ub3d9")),
    ("book_stationery", ("\uc11c\uc810", "\ubb38\uad6c", "\ubb38\ubc29\uad6c", "\ud32c\uc2dc")),
    ("study_cafe", ("\uc2a4\ud130\ub514\uce74\ud398", "\ub3c5\uc11c\uc2e4", "study cafe")),
    ("pc_room", ("pc\ubc29", "\ud53c\uc528\ubc29", "\uc778\ud130\ub137\ucef4\ud4e8\ud130\uac8c\uc784\uc2dc\uc124")),
)


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

def _store_category_from_values(
    *,
    name: Any,
    category_id: str | None,
    category_subcategory_name: Any,
    category_middle_category_name: Any,
    category_main_category_name: Any,
    ksci_subcategory_name: Any,
    ksci_class_name: Any,
    ksci_subclass_name: Any,
    ksci_middle_category_name: Any,
    ksci_main_category_name: Any,
) -> str:
    if category_id == "R10202":
        return "study_cafe"
    haystack = " ".join(
        str(value or "")
        for value in (
            name,
            category_subcategory_name,
            category_middle_category_name,
            category_main_category_name,
            ksci_subcategory_name,
            ksci_class_name,
            ksci_subclass_name,
            ksci_middle_category_name,
            ksci_main_category_name,
        )
    ).lower()
    for category, keywords in STORE_CATEGORY_KEYWORDS:
        if any(keyword.lower() in haystack for keyword in keywords):
            return category
    return "etc"


def _iter_store_rows() -> Iterator[AmenitySourceRow]:
    qs = (
        Store.objects.filter(location__isnull=False)
        .exclude(category_id__in=MEDICAL_STORE_CATEGORY_CODES)
        .values_list(
            "id",
            "name",
            "category_id",
            "category__subcategory_name",
            "category__middle_category_name",
            "category__main_category_name",
            "ksci__subcategory_name",
            "ksci__class_name",
            "ksci__subclass_name",
            "ksci__middle_category_name",
            "ksci__main_category_name",
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
        category_subcategory_name,
        category_middle_category_name,
        category_main_category_name,
        ksci_subcategory_name,
        ksci_class_name,
        ksci_subclass_name,
        ksci_middle_category_name,
        ksci_main_category_name,
        location,
        adong_id,
        ldong_id,
    ) in qs:
        category = _store_category_from_values(
            name=name,
            category_id=category_id,
            category_subcategory_name=category_subcategory_name,
            category_middle_category_name=category_middle_category_name,
            category_main_category_name=category_main_category_name,
            ksci_subcategory_name=ksci_subcategory_name,
            ksci_class_name=ksci_class_name,
            ksci_subclass_name=ksci_subclass_name,
            ksci_middle_category_name=ksci_middle_category_name,
            ksci_main_category_name=ksci_main_category_name,
        )
        if category in STORE_MEDICAL_AMENITY_CATEGORIES:
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


def _iter_univ_rows() -> Iterator[AmenitySourceRow]:
    adongs_by_univ: dict[str, list[str]] = {}
    ldongs_by_univ: dict[str, list[str]] = {}
    for univ_id, adong_id in Univ.objects.filter(adong_links__isnull=False).values_list("id", "adong_links__adong_id"):
        adongs_by_univ.setdefault(univ_id, []).append(adong_id)
    for univ_id, ldong_id in Univ.objects.filter(ldong_links__isnull=False).values_list("id", "ldong_links__ldong_id"):
        ldongs_by_univ.setdefault(univ_id, []).append(ldong_id)
    for univ_id, name, location in Univ.objects.filter(location__isnull=False).values_list("id", "name", "location").iterator(chunk_size=BATCH_SIZE):
        yield AmenitySourceRow("university", _clean_name(name, univ_id), location, "univ", str(univ_id), tuple(adongs_by_univ.get(univ_id, ())), tuple(ldongs_by_univ.get(univ_id, ())))


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
    yield from _iter_medical_rows()
    yield from _iter_park_rows()
    yield from _iter_library_rows()
    yield from _iter_univ_rows()
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
