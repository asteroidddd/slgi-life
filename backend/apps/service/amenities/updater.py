"""Build the derived amenity snapshot from public-data source tables."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from django.contrib.gis.geos import Point
from django.db import transaction

from apps.public_data.bus.models import BusStop
from apps.public_data.library.models import Library
from apps.public_data.park.models import Park
from apps.public_data.store.models import Store
from apps.public_data.subway.models import SubwayStation
from apps.public_data.univ.models import Univ
from apps.service.amenities.models import Amenity, AmenityAdong, AmenityLdong


BATCH_SIZE = 5000

STORE_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("convenience", ("편의점", "슈퍼", "슈퍼마켓")),
    ("mart", ("마트", "대형마트", "식료품")),
    ("restaurant", ("음식", "한식", "중식", "일식", "분식", "양식", "식당", "주점")),
    ("cafe", ("커피", "카페", "다방", "음료")),
    ("studycafe", ("독서실", "스터디", "고시원")),
    ("hospital", ("병원", "의원", "한의원", "의료")),
    ("dental", ("치과",)),
    ("pharmacy", ("약국",)),
    ("laundry", ("세탁", "빨래방")),
    ("oliveyoung", ("올리브영",)),
    ("gym", ("헬스", "체육", "피트니스", "요가", "필라테스")),
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


def _store_category(store: Store) -> str:
    haystack = " ".join(
        str(value or "")
        for value in (
            store.name,
            store.category.subcategory_name if store.category_id else "",
            store.category.middle_category_name if store.category_id else "",
            store.category.main_category_name if store.category_id else "",
            store.ksci.subcategory_name if store.ksci_id else "",
            store.ksci.class_name if store.ksci_id else "",
            store.ksci.subclass_name if store.ksci_id else "",
            store.ksci.middle_category_name if store.ksci_id else "",
            store.ksci.main_category_name if store.ksci_id else "",
        )
    )
    for category, keywords in STORE_CATEGORY_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return category
    return "etc"


def _iter_store_rows() -> Iterator[AmenitySourceRow]:
    qs = (
        Store.objects.select_related("category", "ksci", "adong", "ldong")
        .filter(location__isnull=False)
        .iterator(chunk_size=BATCH_SIZE)
    )
    for store in qs:
        yield AmenitySourceRow(
            category=_store_category(store),
            name=_clean_name(store.name, store.id),
            location=store.location,
            source_table="store",
            source_id=str(store.id),
            adong_ids=(store.adong_id,) if store.adong_id else (),
            ldong_ids=(store.ldong_id,) if store.ldong_id else (),
        )


def _iter_park_rows() -> Iterator[AmenitySourceRow]:
    adongs_by_park: dict[str, list[str]] = {}
    ldongs_by_park: dict[str, list[str]] = {}
    for park_id, adong_id in Park.objects.filter(park_dongs__isnull=False).values_list(
        "id", "park_dongs__adong_id"
    ):
        adongs_by_park.setdefault(park_id, []).append(adong_id)
    for park_id, ldong_id in Park.objects.filter(park_ldongs__isnull=False).values_list(
        "id", "park_ldongs__ldong_id"
    ):
        ldongs_by_park.setdefault(park_id, []).append(ldong_id)

    for park in Park.objects.filter(location__isnull=False).iterator(chunk_size=BATCH_SIZE):
        name = f"{park.name} {park.category}".strip()
        yield AmenitySourceRow(
            category="park",
            name=_clean_name(name, park.id),
            location=park.location,
            source_table="park",
            source_id=str(park.id),
            adong_ids=tuple(adongs_by_park.get(park.id, ())),
            ldong_ids=tuple(ldongs_by_park.get(park.id, ())),
        )


def _iter_library_rows() -> Iterator[AmenitySourceRow]:
    qs = Library.objects.select_related("adong", "ldong").filter(location__isnull=False)
    for library in qs.iterator(chunk_size=BATCH_SIZE):
        yield AmenitySourceRow(
            category="library",
            name=_clean_name(library.name, library.id),
            location=library.location,
            source_table="library",
            source_id=str(library.id),
            adong_ids=(library.adong_id,) if library.adong_id else (),
            ldong_ids=(library.ldong_id,) if library.ldong_id else (),
        )


def _iter_univ_rows() -> Iterator[AmenitySourceRow]:
    adongs_by_univ: dict[str, list[str]] = {}
    ldongs_by_univ: dict[str, list[str]] = {}
    for univ_id, adong_id in Univ.objects.filter(adong_links__isnull=False).values_list(
        "id", "adong_links__adong_id"
    ):
        adongs_by_univ.setdefault(univ_id, []).append(adong_id)
    for univ_id, ldong_id in Univ.objects.filter(ldong_links__isnull=False).values_list(
        "id", "ldong_links__ldong_id"
    ):
        ldongs_by_univ.setdefault(univ_id, []).append(ldong_id)

    for univ in Univ.objects.filter(location__isnull=False).iterator(chunk_size=BATCH_SIZE):
        yield AmenitySourceRow(
            category="university",
            name=_clean_name(univ.name, univ.id),
            location=univ.location,
            source_table="univ",
            source_id=str(univ.id),
            adong_ids=tuple(adongs_by_univ.get(univ.id, ())),
            ldong_ids=tuple(ldongs_by_univ.get(univ.id, ())),
        )


def _iter_subway_rows() -> Iterator[AmenitySourceRow]:
    qs = SubwayStation.objects.select_related("adong", "ldong").filter(location__isnull=False)
    for station in qs.iterator(chunk_size=BATCH_SIZE):
        yield AmenitySourceRow(
            category="subway_station",
            name=_clean_name(f"{station.name}({station.line})", station.id),
            location=station.location,
            source_table="subway_station",
            source_id=str(station.id),
            adong_ids=(station.adong_id,) if station.adong_id else (),
            ldong_ids=(station.ldong_id,) if station.ldong_id else (),
        )


def _iter_bus_rows() -> Iterator[AmenitySourceRow]:
    qs = BusStop.objects.select_related("adong", "ldong").filter(location__isnull=False)
    for stop in qs.iterator(chunk_size=BATCH_SIZE):
        yield AmenitySourceRow(
            category="bus_stop",
            name=_clean_name(stop.name, stop.id),
            location=stop.location,
            source_table="bus_stop",
            source_id=str(stop.id),
            adong_ids=(stop.adong_id,) if stop.adong_id else (),
            ldong_ids=(stop.ldong_id,) if stop.ldong_id else (),
        )


def iter_source_rows() -> Iterator[AmenitySourceRow]:
    yield from _iter_store_rows()
    yield from _iter_park_rows()
    yield from _iter_library_rows()
    yield from _iter_univ_rows()
    yield from _iter_subway_rows()
    yield from _iter_bus_rows()


def rebuild_amenities(*, dry_run: bool = False, batch_size: int = BATCH_SIZE) -> dict[str, Any]:
    """Rebuild Amenity, AmenityAdong and AmenityLdong as a derived snapshot."""

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
            key_to_id = {
                (amenity.source_table, amenity.source_id): amenity.id for amenity in created
            }
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
                adong_links.extend(
                    AmenityAdong(amenity_id=amenity_id, adong_id=adong_id)
                    for adong_id in row.adong_ids
                )
                ldong_links.extend(
                    AmenityLdong(amenity_id=amenity_id, ldong_id=ldong_id)
                    for ldong_id in row.ldong_ids
                )
                stats["by_source"][row.source_table] = (
                    stats["by_source"].get(row.source_table, 0) + 1
                )
                stats["by_category"][row.category] = (
                    stats["by_category"].get(row.category, 0) + 1
                )

            AmenityAdong.objects.bulk_create(
                adong_links, batch_size=batch_size, ignore_conflicts=True
            )
            AmenityLdong.objects.bulk_create(
                ldong_links, batch_size=batch_size, ignore_conflicts=True
            )
            stats["created"] += len(batch)
            stats["links_adong"] += len(adong_links)
            stats["links_ldong"] += len(ldong_links)

    return stats

