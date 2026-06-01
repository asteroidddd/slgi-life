from __future__ import annotations

from django.contrib.gis.geos import Point

from apps.common.geocoding import geocode_address as _geocode_address
from apps.accounts.profile.models import UserProfile


def geocode_address(address: str) -> tuple[Point | None, str, str]:
    query = address.strip()
    if not query:
        return None, "not_provided", ""
    result = _geocode_address(query, user_agent="capston-user-address/0.1")
    if result.status == "success":
        return result.point, "success", ""
    return None, "failed", str(result.error or "address not found")[:255]


def apply_address(profile: UserProfile, address: str | None) -> None:
    cleaned = (address or "").strip()
    profile.address = cleaned
    point, status_value, error = geocode_address(cleaned)
    profile.home_location = point
    profile.address_geocode_status = status_value
    profile.address_geocode_error = error
