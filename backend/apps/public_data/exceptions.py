"""Shared exceptions for public-data updater control flow."""

from __future__ import annotations

from typing import Any


class RateLimitedError(RuntimeError):
    """Raised when an upstream public-data API reports quota/rate limiting."""


RATE_LIMIT_MARKERS = (
    "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR",
    "LIMITED NUMBER OF SERVICE REQUESTS EXCEEDS ERROR",
    "SERVICE REQUESTS EXCEEDS",
    "RATE LIMIT",
    "TOO MANY REQUESTS",
    "QUOTA",
    "쿼터",
    "초과",
)

RATE_LIMIT_CODES = {"22", "429"}


def is_rate_limited_code(value: Any) -> bool:
    return str(value or "").strip().upper() in RATE_LIMIT_CODES


def is_rate_limited_text(value: Any) -> bool:
    text = str(value or "").upper()
    return any(marker in text for marker in RATE_LIMIT_MARKERS)
