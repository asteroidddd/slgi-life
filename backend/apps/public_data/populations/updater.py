"""Population public-data updater for the current capston schema."""

from __future__ import annotations

import os
import socket
import time as sleep_time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from apps.public_data.exceptions import RateLimitedError, is_rate_limited_code, is_rate_limited_text
from apps.public_data.populations.models import AdongPopulation, LdongPopulation
from apps.public_data.regions.models import Adong, Ldong
from apps.public_data.state import load_state, record_dataset_result, save_state


PUBLIC_DATA_BASE_URL = "https://apis.data.go.kr"
LDONG_POPULATION_PATH = "/1741000/stdgPpltnHhStus/selectStdgPpltnHhStus"
ADONG_POPULATION_PATH = "/1741000/admmPpltnHhStus/selectAdmmPpltnHhStus"
DEFAULT_START_YM = "202209"


@dataclass(frozen=True)
class PopulationsUpdateOptions:
    dry_run: bool = True
    limit: int | None = None
    start_ym: str | None = None
    end_ym: str | None = None
    request_interval_seconds: float = 0.2
    request_timeout_seconds: float = 40.0


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _validate_ym(value: str) -> str:
    if len(value) != 6 or not value.isdigit():
        raise ValueError(f"YYYYMM is required: {value}")
    year = int(value[:4])
    month = int(value[4:])
    if year < 2000 or month < 1 or month > 12:
        raise ValueError(f"invalid YYYYMM: {value}")
    return value


def _default_end_ym(today: date | None = None) -> str:
    today = today or date.today()
    year = today.year
    month = today.month - 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year:04d}{month:02d}"


def _next_ym(value: str) -> str:
    year = int(value[:4])
    month = int(value[4:])
    if month == 12:
        return f"{year + 1:04d}01"
    return f"{year:04d}{month + 1:02d}"


def _iter_months(start_ym: str, end_ym: str) -> list[str]:
    start_ym = _validate_ym(start_ym)
    end_ym = _validate_ym(end_ym)
    if start_ym > end_ym:
        return []
    months = []
    current = start_ym
    while current <= end_ym:
        months.append(current)
        current = _next_ym(current)
    return months


def _month_end(ym: str) -> date:
    next_month = _next_ym(ym)
    next_start = date(int(next_month[:4]), int(next_month[4:]), 1)
    return date.fromordinal(next_start.toordinal() - 1)


def _to_int(value: Any) -> int:
    if value in (None, "", "-", "null"):
        raise ValueError("missing population value")
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return int(float(str(value).replace(",", "").strip()))


def _aggregate(items: list[dict[str, str]]) -> tuple[int, int, int, int]:
    total = household = male = female = 0
    for item in items:
        total += _to_int(item.get("totNmprCnt"))
        household += _to_int(item.get("hhCnt"))
        male += _to_int(item.get("maleNmprCnt"))
        female += _to_int(item.get("femlNmprCnt"))
    return total, household, male, female


def _xml_text(node: ET.Element, path: str) -> str | None:
    found = node.find(path)
    if found is None or found.text is None:
        return None
    return found.text.strip()


def _xml_items(root: ET.Element) -> tuple[int, list[dict[str, str]], str | None]:
    result_code = _xml_text(root, "./header/resultCode")
    total_text = _xml_text(root, "./body/totalCount") or "0"
    try:
        total = int(total_text)
    except ValueError:
        total = 0
    items = []
    for item in root.findall(".//item"):
        row = {}
        for child in list(item):
            row[child.tag] = child.text.strip() if child.text else ""
        items.append(row)
    return total, items, result_code


def _request_xml(path: str, params: dict[str, str], options: PopulationsUpdateOptions) -> ET.Element:
    if options.request_interval_seconds:
        sleep_time.sleep(options.request_interval_seconds)
    query = urlencode(params, safe="%")
    url = f"{PUBLIC_DATA_BASE_URL}{path}?{query}"
    req = Request(url, headers={"User-Agent": "capston-public-data-updater/0.1"})
    try:
        with urlopen(req, timeout=options.request_timeout_seconds) as res:
            return ET.fromstring(res.read())
    except HTTPError as exc:
        if exc.code == 429:
            raise RateLimitedError(f"population API rate limited: HTTP 429: {path}") from exc
        raise RuntimeError(f"population API request failed: HTTP {exc.code}: {path}") from exc
    except (URLError, TimeoutError, socket.timeout) as exc:
        raise RuntimeError(f"population API request failed: {type(exc).__name__}: {path}") from exc
    except ET.ParseError as exc:
        raise RuntimeError(f"population API returned malformed XML: {path}") from exc


def _request_xml_with_retry(
    path: str,
    params: dict[str, str],
    options: PopulationsUpdateOptions,
    *,
    attempts: int = 3,
) -> ET.Element:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return _request_xml(path, params, options)
        except RuntimeError as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            sleep_time.sleep(1 + attempt)
    assert last_error is not None
    raise last_error


def _fetch_month(
    *,
    api_key: str,
    path: str,
    code_param: str,
    code: str,
    ym: str,
    options: PopulationsUpdateOptions,
) -> list[dict[str, str]]:
    page = 1
    all_items: list[dict[str, str]] = []
    while True:
        root = _request_xml_with_retry(
            path,
            {
                "serviceKey": api_key,
                code_param: code,
                "srchFrYm": ym,
                "srchToYm": ym,
                "lv": "4",
                "regSeCd": "1",
                "type": "XML",
                "numOfRows": "100",
                "pageNo": str(page),
            },
            options,
        )
        total, items, result_code = _xml_items(root)
        if result_code and result_code not in {"0", "00", "3"}:
            if is_rate_limited_code(result_code) or is_rate_limited_text(result_code):
                raise RateLimitedError(f"population API rate limited resultCode={result_code} code={code} ym={ym}")
            raise RuntimeError(f"population API error resultCode={result_code} code={code} ym={ym}")
        all_items.extend(items)
        if not items or not total or len(all_items) >= total:
            return all_items
        page += 1


def _missing_months(model, fk_field: str, expected_count: int, months: list[str]) -> list[str]:
    missing = []
    for ym in months:
        count = model.objects.filter(date=_month_end(ym)).values(fk_field).distinct().count()
        if count < expected_count:
            missing.append(ym)
    return missing


def _load_domain(
    *,
    api_key: str,
    domain: str,
    codes: list[str],
    model,
    path: str,
    code_param: str,
    fk_field: str,
    months: list[str],
    options: PopulationsUpdateOptions,
    checked_so_far: int,
) -> dict[str, Any]:
    checked = loaded = skipped_empty = 0
    completed = False

    try:
        for ym in months:
            for code in codes:
                if options.limit is not None and checked_so_far + checked >= options.limit:
                    return {
                        "domain": domain,
                        "status": "partial",
                        "completed": False,
                        "checked": checked,
                        "loaded": loaded,
                        "skipped_empty": skipped_empty,
                        "months": months,
                    }
                items = _fetch_month(
                    api_key=api_key,
                    path=path,
                    code_param=code_param,
                    code=code,
                    ym=ym,
                    options=options,
                )
                checked += 1
                if not items:
                    skipped_empty += 1
                    continue
                try:
                    total, household, male, female = _aggregate(items)
                except ValueError as exc:
                    raise RuntimeError(
                        f"population malformed value domain={domain} code={code} ym={ym}: {exc}"
                    ) from exc
                if not options.dry_run:
                    model.objects.update_or_create(
                        **{fk_field: code, "date": _month_end(ym)},
                        defaults={
                            "total_population": total,
                            "household_count": household,
                            "male_population": male,
                            "female_population": female,
                        },
                    )
                    loaded += 1
        completed = True
    except RateLimitedError as exc:
        return {
            "domain": domain,
            "status": "rate_limited",
            "completed": False,
            "checked": checked,
            "loaded": loaded,
            "skipped_empty": skipped_empty,
            "months": months,
            "error": str(exc),
        }

    return {
        "domain": domain,
        "status": "success" if completed else "partial",
        "completed": completed,
        "checked": checked,
        "loaded": loaded,
        "skipped_empty": skipped_empty,
        "months": months,
    }


def update_populations(options: PopulationsUpdateOptions) -> dict[str, Any]:
    start_ym = _validate_ym(options.start_ym or DEFAULT_START_YM)
    end_ym = _validate_ym(options.end_ym or _default_end_ym())
    months = _iter_months(start_ym, end_ym)

    ldong_codes = list(Ldong.objects.order_by("ldong_code").values_list("ldong_code", flat=True))
    adong_codes = list(Adong.objects.order_by("adong_code").values_list("adong_code", flat=True))
    before_missing = {
        "ldong": _missing_months(LdongPopulation, "ldong_id", len(ldong_codes), months),
        "adong": _missing_months(AdongPopulation, "adong_id", len(adong_codes), months),
    }

    if not before_missing["ldong"] and not before_missing["adong"]:
        return {
            "status": "success",
            "completed": True,
            "loaded": 0,
            "dry_run": options.dry_run,
            "loaded_start": None,
            "loaded_end": None,
            "expected": {"ldong": len(ldong_codes), "adong": len(adong_codes)},
            "missing_months": before_missing,
            "after_missing_months": before_missing,
            "skipped_write": True,
            "reason": "no_missing_months",
            "domains": [],
        }

    api_key = _require_env("PUBLIC_DATA_API_KEY")
    results = []
    checked_total = 0

    ldong_result = _load_domain(
        api_key=api_key,
        domain="ldong",
        codes=ldong_codes,
        model=LdongPopulation,
        path=LDONG_POPULATION_PATH,
        code_param="stdgCd",
        fk_field="ldong_id",
        months=sorted(before_missing["ldong"], reverse=True),
        options=options,
        checked_so_far=checked_total,
    )
    results.append(ldong_result)
    checked_total += ldong_result["checked"]

    adong_result = _load_domain(
        api_key=api_key,
        domain="adong",
        codes=adong_codes,
        model=AdongPopulation,
        path=ADONG_POPULATION_PATH,
        code_param="admmCd",
        fk_field="adong_id",
        months=sorted(before_missing["adong"], reverse=True),
        options=options,
        checked_so_far=checked_total,
    )
    results.append(adong_result)

    after_missing = before_missing
    if not options.dry_run:
        after_missing = {
            "ldong": _missing_months(LdongPopulation, "ldong_id", len(ldong_codes), months),
            "adong": _missing_months(AdongPopulation, "adong_id", len(adong_codes), months),
        }

    completed = (
        all(result["completed"] for result in results)
        and not after_missing["ldong"]
        and not after_missing["adong"]
    )
    loaded = sum(result["loaded"] for result in results)
    loaded_months = sorted(set(before_missing["ldong"] + before_missing["adong"]))

    return {
        "status": "success" if completed else "partial",
        "completed": completed,
        "loaded": loaded,
        "dry_run": options.dry_run,
        "loaded_start": loaded_months[0] if loaded_months else None,
        "loaded_end": loaded_months[-1] if loaded_months else None,
        "expected": {"ldong": len(ldong_codes), "adong": len(adong_codes)},
        "missing_months": before_missing,
        "after_missing_months": after_missing,
        "domains": results,
    }


def update(options: PopulationsUpdateOptions) -> dict[str, Any]:
    result: dict[str, Any] = {
        "dataset": "populations",
        "dry_run": options.dry_run,
        "populations": None,
    }
    try:
        result["populations"] = update_populations(options)
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if not options.dry_run:
            record_dataset_result("populations", result)
        raise

    if not options.dry_run:
        record_dataset_result("populations", result)
        if result["populations"] and result["populations"].get("completed"):
            state = load_state()
            populations_state = state.setdefault("datasets", {}).setdefault("populations", {})
            populations_state["populations"] = {
                "last_success_month": result["populations"].get("loaded_end") or options.end_ym or _default_end_ym(),
                "loaded_start": result["populations"].get("loaded_start"),
                "loaded_end": result["populations"].get("loaded_end"),
                "missing_months": result["populations"].get("after_missing_months"),
                "expected": result["populations"].get("expected"),
            }
            save_state(state)
    return result
