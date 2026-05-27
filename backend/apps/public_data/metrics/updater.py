"""Metrics public-data updater for the current capston schema."""

from __future__ import annotations

import json
import os
import socket
import time as sleep_time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db import transaction
from django.db.models import Avg, Count

from apps.public_data.exceptions import RateLimitedError, is_rate_limited_text
from apps.public_data.metrics.catalog import METRIC_CATALOG
from apps.public_data.metrics.models import GuMetric, Metric, SeoulMetric
from apps.public_data.regions.models import Gu
from apps.public_data.state import load_state, record_dataset_result, save_state


KOSIS_BASE_URL = "https://kosis.kr/openapi"
KOSIS_STATISTICS_PATH = "/Param/statisticsParameterData.do"
SEOUL_TOTAL_CODE = "11"
DEFAULT_DISTRICT_CODES = [
    "11010",
    "11020",
    "11030",
    "11040",
    "11050",
    "11060",
    "11070",
    "11080",
    "11090",
    "11100",
    "11110",
    "11120",
    "11130",
    "11140",
    "11150",
    "11160",
    "11170",
    "11180",
    "11190",
    "11200",
    "11210",
    "11220",
    "11230",
    "11240",
    "11250",
]
ADMIN_DISTRICT_CODES = [
    "11110",
    "11140",
    "11170",
    "11200",
    "11215",
    "11230",
    "11260",
    "11290",
    "11305",
    "11320",
    "11350",
    "11380",
    "11410",
    "11440",
    "11470",
    "11500",
    "11530",
    "11545",
    "11560",
    "11590",
    "11620",
    "11650",
    "11680",
    "11710",
    "11740",
]
GREEN_SEOUL_TOTAL_CODE = "15315SGG01"
GREEN_DISTRICT_CODES = [f"15315SGG01{i:02d}" for i in range(1, 26)]

TABLE_SPECS = [
    {"tblId": "DT_1YL20631", "itmId": "T10 T002", "prdSe": "M", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": ""},
    {"tblId": "INH_1IN1503_02", "itmId": "T00 T01 T02", "prdSe": "Y", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": "ALL"},
    {"tblId": "DT_1YL20643", "itmId": "T001", "prdSe": "Y", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": "11 12 13 21 22 23 31 32 33"},
    {"tblId": "DT_1YL20651E", "itmId": "T20 T21 T22", "prdSe": "M", "objL1": " ".join([SEOUL_TOTAL_CODE] + ADMIN_DISTRICT_CODES), "objL2": ""},
    {"tblId": "DT_1YL20331", "itmId": "T01", "prdSe": "Y", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": "ALL"},
    {"tblId": "DT_1YL14001", "itmId": "T10 T001 T002", "prdSe": "Y", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": ""},
    {"tblId": "DT_1YL13901", "itmId": "T10 T001 T002", "prdSe": "Y", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": ""},
    {"tblId": "DT_1YL21051", "itmId": "T10 T001 T002", "prdSe": "Y", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": ""},
    {"tblId": "DT_1YL8601", "itmId": "T10", "prdSe": "Y", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": ""},
    {"tblId": "DT_1YL20341", "itmId": "T10", "prdSe": "Y", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": "ALL"},
    {"tblId": "INH_1JU1501", "itmId": "T10", "prdSe": "Y", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": ""},
    {"tblId": "DT_1YL20881E", "itmId": "13103890822T1", "prdSe": "M", "objL1": " ".join([SEOUL_TOTAL_CODE] + ADMIN_DISTRICT_CODES), "objL2": ""},
    {"tblId": "DT_1C65_03E", "itmId": "Z10 Z20", "prdSe": "Y", "objL1": " ".join([SEOUL_TOTAL_CODE] + DEFAULT_DISTRICT_CODES), "objL2": ""},
    {"tblId": "DT_1YL202105E", "itmId": "16315T2009_046 T01", "prdSe": "Y", "objL1": " ".join([GREEN_SEOUL_TOTAL_CODE] + GREEN_DISTRICT_CODES), "objL2": "ALL"},
]


@dataclass(frozen=True)
class MetricsUpdateOptions:
    dry_run: bool = True
    limit: int | None = None
    request_interval_seconds: float = 0.2
    request_timeout_seconds: float = 40.0


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _request_json(path: str, params: dict[str, str], options: MetricsUpdateOptions) -> Any:
    if options.request_interval_seconds:
        sleep_time.sleep(options.request_interval_seconds)
    query = urlencode(params, doseq=True, safe="%")
    url = f"{KOSIS_BASE_URL}{path}?{query}"
    req = Request(url, headers={"User-Agent": "capston-public-data-updater/0.1"})
    try:
        with urlopen(req, timeout=options.request_timeout_seconds) as res:
            return json.loads(res.read().decode("utf-8", errors="replace"))
    except HTTPError as exc:
        if exc.code == 429:
            raise RateLimitedError(f"KOSIS rate limited: HTTP 429: {path}") from exc
        raise RuntimeError(f"KOSIS request failed: HTTP {exc.code}: {path}") from exc
    except (URLError, TimeoutError, socket.timeout) as exc:
        raise RuntimeError(f"KOSIS request failed: {type(exc).__name__}: {path}") from exc


def _source_mapping() -> dict[tuple[str | None, str | None, str | None], dict[str, Any]]:
    mapping = {}
    for row in METRIC_CATALOG:
        if not row.get("is_generated"):
            mapping[
                (
                    row.get("source_table"),
                    row.get("source_item"),
                    row.get("source_classification_code"),
                )
            ] = row
    return mapping


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _date(row: dict[str, Any]) -> date | None:
    prd = str(row.get("PRD_DE") or "").strip()
    if len(prd) == 6:
        return date(int(prd[:4]), int(prd[4:6]), 1)
    if len(prd) == 4:
        return date(int(prd), 1, 1)
    return None


def _region(row: dict[str, Any], name_to_gu: dict[str, str]) -> tuple[str | None, str | None]:
    name = str(row.get("C1_NM") or "").replace("서울 ", "").strip()
    if "서울" in name and "구" not in name:
        return "seoul", "11"
    if name in name_to_gu:
        return "gu", name_to_gu[name]
    code = str(row.get("C1") or "").strip()
    if code in ADMIN_DISTRICT_CODES:
        return "gu", code
    return None, None


def _insert_catalog(*, dry_run: bool) -> dict[str, int]:
    checked = len(METRIC_CATALOG)
    loaded = 0
    if not dry_run:
        for row in METRIC_CATALOG:
            Metric.objects.update_or_create(
                metric_code=row["metric_code"],
                defaults={key: row[key] for key in row if key != "metric_code"},
            )
            loaded += 1
    return {"checked": checked, "loaded": loaded}


def _fetch_sources(options: MetricsUpdateOptions) -> dict[str, Any]:
    api_key = _require_env("KOSIS_API_KEY")
    mapping = _source_mapping()
    name_to_gu = {gu.name: gu.gu_code for gu in Gu.objects.all()}
    checked = loaded_gu = loaded_seoul = skipped = 0
    skip_reasons = {"bad_row": 0, "unknown_metric": 0, "unknown_region": 0}
    dates: list[date] = []
    table_stats: dict[str, dict[str, int]] = {}
    completed = False

    for spec in TABLE_SPECS:
        table_id = spec["tblId"]
        table_stats.setdefault(table_id, {"checked": 0, "loaded_gu": 0, "loaded_seoul": 0, "skipped": 0})
        rows = _request_json(
            KOSIS_STATISTICS_PATH,
            {
                "method": "getList",
                "apiKey": api_key,
                "format": "json",
                "jsonVD": "Y",
                "newEstPrdCnt": "400",
                "orgId": "101",
                "tblId": spec["tblId"],
                "itmId": spec["itmId"],
                "objL1": spec["objL1"],
                "objL2": spec["objL2"],
                "objL3": "",
                "objL4": "",
                "objL5": "",
                "objL6": "",
                "objL7": "",
                "objL8": "",
                "prdSe": spec["prdSe"],
            },
            options,
        )
        if isinstance(rows, dict):
            if is_rate_limited_text(rows):
                raise RateLimitedError(f"KOSIS rate limited: {rows}")
            rows = []
        ordered_rows = sorted(rows or [], key=lambda row: str(row.get("PRD_DE") or ""), reverse=True)
        for row in ordered_rows:
            checked += 1
            table_stats[table_id]["checked"] += 1
            c2 = str(row.get("C2") or "").strip() or None
            meta = mapping.get(
                (
                    str(row.get("TBL_ID") or "").strip(),
                    str(row.get("ITM_ID") or "").strip(),
                    c2,
                )
            )
            value = _to_decimal(row.get("DT"))
            date_value = _date(row)
            kind, code = _region(row, name_to_gu)
            if not meta:
                skipped += 1
                skip_reasons["unknown_metric"] += 1
                table_stats[table_id]["skipped"] += 1
                continue
            if not kind:
                skipped += 1
                skip_reasons["unknown_region"] += 1
                table_stats[table_id]["skipped"] += 1
                continue
            if value is None or date_value is None:
                skipped += 1
                skip_reasons["bad_row"] += 1
                table_stats[table_id]["skipped"] += 1
                continue

            dates.append(date_value)
            if not options.dry_run:
                if kind == "seoul":
                    SeoulMetric.objects.update_or_create(
                        seoul_id="11",
                        metric_id=meta["metric_code"],
                        date=date_value,
                        defaults={"value": value},
                    )
                    loaded_seoul += 1
                    table_stats[table_id]["loaded_seoul"] += 1
                else:
                    GuMetric.objects.update_or_create(
                        gu_id=code,
                        metric_id=meta["metric_code"],
                        date=date_value,
                        defaults={"value": value},
                    )
                    loaded_gu += 1
                    table_stats[table_id]["loaded_gu"] += 1

            if options.limit is not None and checked >= options.limit:
                return {
                    "status": "partial",
                    "completed": False,
                    "checked": checked,
                    "loaded_gu": loaded_gu,
                    "loaded_seoul": loaded_seoul,
                    "skipped": skipped,
                    "loaded_start": min(dates).isoformat() if dates else None,
                    "loaded_end": max(dates).isoformat() if dates else None,
                    "skip_reasons": skip_reasons,
                    "tables": table_stats,
                }
    completed = checked > 0 and bool(dates)
    return {
        "status": "success" if completed else "partial",
        "completed": completed,
        "checked": checked,
        "loaded_gu": loaded_gu,
        "loaded_seoul": loaded_seoul,
        "skipped": skipped,
        "loaded_start": min(dates).isoformat() if dates else None,
        "loaded_end": max(dates).isoformat() if dates else None,
        "skip_reasons": skip_reasons,
        "tables": table_stats,
    }


def _safe_div(num: Decimal, den: Decimal | None, mult: int = 1) -> Decimal | None:
    if den in (None, 0):
        return None
    return (Decimal(num) / Decimal(den)) * Decimal(mult)


def _load_derived(*, dry_run: bool) -> dict[str, int]:
    if dry_run:
        return {"loaded_gu": 0, "loaded_seoul": 0}

    loaded_gu = loaded_seoul = 0
    ratio_rules = [
        ("ACC_DRUNK_RATIO", "ACC_DRUNK_COUNT", "ACC_INJURY_COUNT", 100),
        ("ACC_HITRUN_RATIO", "ACC_HITRUN_COUNT", "ACC_INJURY_COUNT", 100),
        ("ACC_PER_1K_VEHICLE", "ACC_TOTAL_COUNT", "VEHICLE_REGISTERED", 1000),
        ("AREA_GREEN_RATIO", "AREA_GREEN", "AREA_URBAN", 100),
        ("POP_FEMALE_RATIO", "POP_RESIDENT_FEMALE", "POP_RESIDENT", 100),
        ("POP_MALE_RATIO", "POP_RESIDENT_MALE", "POP_RESIDENT", 100),
        ("POP_YOUTH_RATIO_19_34", "POP_YOUTH_19_34", "POP_TOTAL_YOUTH_BASE", 100),
        ("POP_YOUTH_RATIO_19_39", "POP_YOUTH_19_39", "POP_TOTAL_YOUTH_BASE", 100),
    ]
    for out_code, num_code, den_code, mult in ratio_rules:
        for model, key_field in ((GuMetric, "gu_id"), (SeoulMetric, "seoul_id")):
            nums = {(getattr(row, key_field), row.date): row.value for row in model.objects.filter(metric_id=num_code)}
            dens = {(getattr(row, key_field), row.date): row.value for row in model.objects.filter(metric_id=den_code)}
            for key, num in nums.items():
                value = _safe_div(num, dens.get(key), mult)
                if value is None:
                    continue
                obj_key, date_value = key
                model.objects.update_or_create(
                    **{key_field: obj_key, "metric_id": out_code, "date": date_value},
                    defaults={"value": value},
                )
                if model is GuMetric:
                    loaded_gu += 1
                else:
                    loaded_seoul += 1

    annual_rules = [
        ("ACC_PER_10K_POP", "ACC_TOTAL_COUNT", 10000),
        ("VEHICLE_PER_10K_POP", "VEHICLE_REGISTERED", 10000),
        ("AREA_GREEN_PER_CAPITA", "AREA_GREEN", 1),
        ("GRDP_PER_CAPITA", "GRDP_CURRENT", 1),
        ("HOUSING_PER_CAPITA", "HOUSING_COUNT", 1),
    ]
    for model, key_field in ((GuMetric, "gu_id"), (SeoulMetric, "seoul_id")):
        pop_rows = (
            model.objects.filter(metric_id="POP_TOTAL")
            .values(key_field, "date__year")
            .annotate(avg=Avg("value"), n=Count("id"))
            .filter(n=12)
        )
        pop = {(row[key_field], row["date__year"]): row["avg"] for row in pop_rows}
        for out_code, num_code, mult in annual_rules:
            for row in model.objects.filter(metric_id=num_code):
                value = _safe_div(row.value, pop.get((getattr(row, key_field), row.date.year)), mult)
                if value is None:
                    continue
                model.objects.update_or_create(
                    **{key_field: getattr(row, key_field), "metric_id": out_code, "date": row.date},
                    defaults={"value": value},
                )
                if model is GuMetric:
                    loaded_gu += 1
                else:
                    loaded_seoul += 1

    for model, key_field in ((GuMetric, "gu_id"), (SeoulMetric, "seoul_id")):
        base: dict[tuple[str, date], dict[str, Decimal]] = defaultdict(dict)
        for row in model.objects.filter(
            metric_id__in=[
                "SAFETY_GRADE_TRAFFIC",
                "SAFETY_GRADE_FIRE",
                "SAFETY_GRADE_CRIME",
                "SAFETY_GRADE_LIFE",
                "SAFETY_GRADE_SUICIDE",
                "SAFETY_GRADE_DISEASE",
            ]
        ):
            base[(getattr(row, key_field), row.date)][row.metric_id] = row.value
        for (obj_key, date_value), values in base.items():
            if len(values) != 6:
                continue
            model.objects.update_or_create(
                **{key_field: obj_key, "metric_id": "SAFETY_GRADE_MEAN", "date": date_value},
                defaults={"value": sum(values.values()) / Decimal(6)},
            )
            if model is GuMetric:
                loaded_gu += 1
            else:
                loaded_seoul += 1

    return {"loaded_gu": loaded_gu, "loaded_seoul": loaded_seoul}


def update_metrics(options: MetricsUpdateOptions) -> dict[str, Any]:
    with transaction.atomic():
        catalog = _insert_catalog(dry_run=options.dry_run)
        kosis = _fetch_sources(options)
        derived = _load_derived(dry_run=options.dry_run) if kosis["completed"] else {"loaded_gu": 0, "loaded_seoul": 0}

    loaded = catalog["loaded"] + kosis["loaded_gu"] + kosis["loaded_seoul"] + derived["loaded_gu"] + derived["loaded_seoul"]
    return {
        "status": "success" if kosis["completed"] else "partial",
        "completed": kosis["completed"],
        "loaded": loaded,
        "dry_run": options.dry_run,
        "catalog": catalog,
        "kosis": kosis,
        "derived": derived,
        "loaded_start": kosis["loaded_start"],
        "loaded_end": kosis["loaded_end"],
    }


def update(options: MetricsUpdateOptions) -> dict[str, Any]:
    result: dict[str, Any] = {
        "dataset": "metrics",
        "dry_run": options.dry_run,
        "metrics": None,
    }
    try:
        result["metrics"] = update_metrics(options)
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if not options.dry_run:
            record_dataset_result("metrics", result)
        raise

    if not options.dry_run:
        record_dataset_result("metrics", result)
        if result["metrics"] and result["metrics"].get("completed"):
            state = load_state()
            metrics_state = state.setdefault("datasets", {}).setdefault("metrics", {})
            loaded_end = result["metrics"].get("loaded_end")
            metrics_state["metrics"] = {
                "last_success_date": loaded_end,
                "loaded_start": result["metrics"].get("loaded_start"),
                "loaded_end": loaded_end,
                "catalog_count": result["metrics"]["catalog"]["checked"],
            }
            save_state(state)
    return result
