"""Small JSON state store for public-data update jobs."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_PATH = Path(__file__).resolve().parent / ".state" / "public_data_state.json"


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"datasets": {}}
    with STATE_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"datasets": {}}
    data.setdefault("datasets", {})
    return data


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_PATH.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp_path, STATE_PATH)


def dataset_state(dataset: str) -> dict[str, Any]:
    state = load_state()
    datasets = state.setdefault("datasets", {})
    value = datasets.setdefault(dataset, {})
    return value if isinstance(value, dict) else {}


def _result_success(result: dict[str, Any]) -> bool:
    if result.get("dry_run") or result.get("error"):
        return False
    for value in result.values():
        if not isinstance(value, dict):
            continue
        if value.get("status") in {"error", "partial"}:
            return False
        if value.get("completed") is False:
            return False
    return True


def record_dataset_result(dataset: str, result: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    datasets = state.setdefault("datasets", {})
    current = datasets.setdefault(dataset, {})
    if not isinstance(current, dict):
        current = {}
        datasets[dataset] = current

    current["last_run_at"] = utc_now_iso()
    current["last_result"] = result
    if _result_success(result):
        current["last_success_at"] = current["last_run_at"]
    else:
        current["last_failed_at"] = current["last_run_at"]

    save_state(state)
    return current
