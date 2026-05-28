from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from typing import TypeVar

from apps.public_data.exceptions import RateLimitedError


T = TypeVar("T")


def env_key_ring(primary_name: str) -> tuple[str, ...]:
    """Return primary key plus numbered fallback keys, preserving order."""
    names = [primary_name, *(f"{primary_name}{index}" for index in range(2, 10))]
    seen: set[str] = set()
    keys: list[str] = []
    for name in names:
        value = os.environ.get(name, "").strip()
        if value and value not in seen:
            keys.append(value)
            seen.add(value)
    if not keys:
        raise RuntimeError(f"{primary_name} is required")
    return tuple(keys)


def with_rate_limit_fallback(keys: Iterable[str], call: Callable[[str], T]) -> T:
    last_error: RateLimitedError | None = None
    for key in keys:
        try:
            return call(key)
        except RateLimitedError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise RuntimeError("no API keys configured")
