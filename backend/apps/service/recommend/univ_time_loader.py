from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction

from apps.public_data.regions.models import Adong, Ldong
from apps.public_data.univ.models import Univ
from apps.service.recommend.models import AdongUnivTime, LdongUnivTime


ADONG_UNIV_TIME_CSV = "adong_univ_time.csv"
LDONG_UNIV_TIME_CSV = "ldong_univ_time.csv"


@dataclass(frozen=True)
class UnivTimeImportSummary:
    adong_rows: int
    ldong_rows: int
    adong_codes: int
    ldong_codes: int
    univ_codes: int
    dry_run: bool = False


def default_data_dir() -> Path:
    return Path(settings.BASE_DIR) / "data"


def import_univ_times_from_csv(
    *,
    data_dir: Path | None = None,
    dry_run: bool = False,
) -> UnivTimeImportSummary:
    base = data_dir or default_data_dir()
    adong_rows = _load_csv(base / ADONG_UNIV_TIME_CSV, "adong_code")
    ldong_rows = _load_csv(base / LDONG_UNIV_TIME_CSV, "ldong_code")

    _validate_rows(adong_rows, "adong_code", Adong, "adong_code")
    _validate_rows(ldong_rows, "ldong_code", Ldong, "ldong_code")
    _validate_univs(adong_rows, ldong_rows)

    summary = UnivTimeImportSummary(
        adong_rows=len(adong_rows),
        ldong_rows=len(ldong_rows),
        adong_codes=len({row["adong_code"] for row in adong_rows}),
        ldong_codes=len({row["ldong_code"] for row in ldong_rows}),
        univ_codes=len({row["univ_code"] for row in adong_rows + ldong_rows}),
        dry_run=dry_run,
    )

    if dry_run:
        return summary

    with transaction.atomic():
        AdongUnivTime.objects.all().delete()
        LdongUnivTime.objects.all().delete()
        AdongUnivTime.objects.bulk_create(
            [
                AdongUnivTime(
                    adong_id=row["adong_code"],
                    univ_id=row["univ_code"],
                    time=row["time"],
                )
                for row in adong_rows
            ],
            batch_size=5000,
        )
        LdongUnivTime.objects.bulk_create(
            [
                LdongUnivTime(
                    ldong_id=row["ldong_code"],
                    univ_id=row["univ_code"],
                    time=row["time"],
                )
                for row in ldong_rows
            ],
            batch_size=5000,
        )
    return summary


def _load_csv(path: Path, code_field: str) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        required = {code_field, "univ_code", "time"}
        missing_columns = required - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"{path.name} missing columns: {sorted(missing_columns)}")

        for line_no, row in enumerate(reader, start=2):
            region_code = str(row.get(code_field) or "").strip()
            univ_code = str(row.get("univ_code") or "").strip()
            raw_time = str(row.get("time") or "").strip()
            if not region_code or not univ_code or not raw_time:
                raise ValueError(f"{path.name}:{line_no} has empty required value.")
            try:
                minutes = int(raw_time)
            except ValueError as exc:
                raise ValueError(f"{path.name}:{line_no} time is not integer: {raw_time}") from exc
            if minutes <= 0:
                raise ValueError(f"{path.name}:{line_no} time must be positive: {minutes}")

            key = (region_code, univ_code)
            if key in seen:
                raise ValueError(f"{path.name}:{line_no} duplicate key: {key}")
            seen.add(key)
            rows.append({code_field: region_code, "univ_code": univ_code, "time": minutes})
    return rows


def _validate_rows(rows: list[dict[str, Any]], code_field: str, model: type, model_code_field: str) -> None:
    csv_codes = {row[code_field] for row in rows}
    db_codes = set(model.objects.filter(**{f"{model_code_field}__in": csv_codes}).values_list(model_code_field, flat=True))
    missing = sorted(csv_codes - db_codes)
    if missing:
        raise ValueError(f"{code_field} values missing in DB: {missing[:20]} (total {len(missing)})")


def _validate_univs(*row_groups: list[dict[str, Any]]) -> None:
    csv_codes = {row["univ_code"] for rows in row_groups for row in rows}
    db_codes = set(Univ.objects.filter(id__in=csv_codes).values_list("id", flat=True))
    missing = sorted(csv_codes - db_codes)
    if missing:
        raise ValueError(f"univ_code values missing in DB: {missing[:20]} (total {len(missing)})")
