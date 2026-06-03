from __future__ import annotations

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.favorites.models import CandidateRegion, Favorite
from apps.accounts.favorites.serializers import FavoriteItemSerializer, build_favorite_item
from apps.accounts.user.authentication import AuthRequiredMixin
from apps.public_data.regions.models import Adong, Ldong

MAX_CANDIDATES = 10
USER_CACHE_TTL_SECONDS = 60 * 60 * 24 * 365


def _candidate_cache_key(user_id: int) -> str:
    return f"user:{user_id}:candidate-regions:v1"


def _conditions_cache_key(user_id: int) -> str:
    return f"user:{user_id}:recommendation-conditions:v1"


def _clean_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _clean_candidate(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    region_level = item.get("regionLevel")
    slug = item.get("slug")
    gu = item.get("gu")
    name = item.get("name")
    if region_level not in {"adong", "ldong"}:
        return None
    if not all(isinstance(value, str) and value.strip() for value in (slug, gu, name)):
        return None
    source = item.get("source")
    if source not in {"conditions", "map", "detail"}:
        source = "map"
    added_at = int(_clean_number(item.get("addedAt")) or 0)
    cleaned = {
        "regionLevel": region_level,
        "slug": slug.strip(),
        "gu": gu.strip(),
        "name": name.strip(),
        "source": source,
        "addedAt": added_at,
    }
    for key in ("code",):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            cleaned[key] = value.strip()
    for key in ("lat", "lng", "score", "score_rent", "score_transit", "score_amenity", "score_safety"):
        value = _clean_number(item.get(key))
        if value is not None:
            cleaned[key] = value
    return cleaned


def _candidate_model_to_item(candidate: CandidateRegion) -> dict:
    item = {
        "regionLevel": candidate.region_level,
        "slug": candidate.slug,
        "gu": candidate.gu,
        "name": candidate.name,
        "source": candidate.source,
        "addedAt": candidate.added_at_ms,
    }
    if candidate.code:
        item["code"] = candidate.code
    for api_key, model_key in (
        ("lat", "lat"),
        ("lng", "lng"),
        ("score", "score"),
        ("score_rent", "score_rent"),
        ("score_transit", "score_transit"),
        ("score_amenity", "score_amenity"),
        ("score_safety", "score_safety"),
    ):
        value = getattr(candidate, model_key)
        if value is not None:
            item[api_key] = value
    return item


def _current_region_item(item: dict, region) -> dict:
    next_item = {
        **item,
        "code": getattr(region, "adong_code", None) or getattr(region, "ldong_code", None) or item.get("code", ""),
        "gu": region.gu.name if getattr(region, "gu", None) else item["gu"],
        "name": region.name,
    }
    if getattr(region, "location", None):
        next_item["lat"] = region.location.y
        next_item["lng"] = region.location.x

    current = getattr(region, "current_score", None)
    score_values = {
        "score": getattr(current, "score_total", None) if current else None,
        "score_rent": getattr(current, "score_rent", None) if current else None,
        "score_transit": getattr(current, "score_transit", None) if current else None,
        "score_amenity": getattr(current, "score_amenity", None) if current else None,
        "score_safety": getattr(current, "score_safety", None) if current else None,
    }
    for key, value in score_values.items():
        if value is None:
            next_item.pop(key, None)
        else:
            next_item[key] = float(value)
    return next_item


def _candidate_without_scores(item: dict) -> dict:
    next_item = {**item}
    for key in ("score", "score_rent", "score_transit", "score_amenity", "score_safety"):
        next_item.pop(key, None)
    return next_item


def _hydrate_candidate_regions(items: list[dict]) -> list[dict]:
    if not items:
        return []
    adong_slugs = [item["slug"] for item in items if item["regionLevel"] == "adong"]
    ldong_slugs = [item["slug"] for item in items if item["regionLevel"] == "ldong"]
    adongs = {
        region.slug: region
        for region in Adong.objects.select_related("gu", "current_score").filter(slug__in=adong_slugs)
    }
    ldongs = {
        region.slug: region
        for region in Ldong.objects.select_related("gu", "current_score").filter(slug__in=ldong_slugs)
    }

    hydrated: list[dict] = []
    for item in items:
        region = adongs.get(item["slug"]) if item["regionLevel"] == "adong" else ldongs.get(item["slug"])
        hydrated.append(_current_region_item(item, region) if region else _candidate_without_scores(item))
    return hydrated


def _candidate_model_kwargs(user, item: dict) -> dict:
    kwargs = {
        "user": user,
        "region_level": item["regionLevel"],
        "slug": item["slug"],
        "code": item.get("code", ""),
        "gu": item["gu"],
        "name": item["name"],
        "source": item["source"],
        "added_at_ms": item["addedAt"],
    }
    for key in ("lat", "lng", "score", "score_rent", "score_transit", "score_amenity", "score_safety"):
        if key in item:
            kwargs[key] = item[key]
    return kwargs


def _replace_candidate_regions(user, items: list[dict]) -> list[dict]:
    items = _hydrate_candidate_regions(items)
    with transaction.atomic():
        CandidateRegion.objects.filter(user=user).delete()
        CandidateRegion.objects.bulk_create([
            CandidateRegion(**_candidate_model_kwargs(user, item))
            for item in items
        ])
    cache.delete(_candidate_cache_key(user.id))
    return [
        _candidate_model_to_item(candidate)
        for candidate in CandidateRegion.objects.filter(user=user)
    ]


def _load_candidate_regions(user) -> list[dict]:
    db_items = [
        _candidate_model_to_item(candidate)
        for candidate in CandidateRegion.objects.filter(user=user)
    ]
    return _hydrate_candidate_regions(db_items)


def _clean_candidates(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for raw in value:
        item = _clean_candidate(raw)
        if item is None:
            continue
        key = (item["regionLevel"], item["slug"])
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
        if len(items) >= MAX_CANDIDATES:
            break
    return items


def _clean_conditions(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    priority = value.get("priority")
    if priority not in {"budget", "transport"}:
        priority = "budget"
    facilities = value.get("facilities")
    cleaned_facilities = [
        item for item in facilities
        if isinstance(item, str) and item.strip()
    ] if isinstance(facilities, list) else []
    return {
        "deposit": _clean_number(value.get("deposit")) or 0,
        "monthlyRent": _clean_number(value.get("monthlyRent")) or 0,
        "areaM2": _clean_number(value.get("areaM2")),
        "facilities": cleaned_facilities[:20],
        "universityId": value.get("universityId") if isinstance(value.get("universityId"), str) else "",
        "universityName": value.get("universityName") if isinstance(value.get("universityName"), str) else "",
        "maxCommuteMinutes": _clean_number(value.get("maxCommuteMinutes")) or 0,
        "priority": priority,
    }


@extend_schema(tags=["users"], summary="Favorites")
@method_decorator(csrf_exempt, name="dispatch")
class FavoritesView(AuthRequiredMixin, APIView):
    def get(self, request: Request) -> Response:
        favs = Favorite.objects.filter(user=request.user).select_related(
            "adong", "adong__gu", "adong__current_score"
        )
        items = [build_favorite_item(f) for f in favs]
        return Response(FavoriteItemSerializer(items, many=True).data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        slug = (request.data or {}).get("slug")
        if not isinstance(slug, str) or not slug.strip():
            return Response({"slug": "slug is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            adong = Adong.objects.select_related("gu", "current_score").get(slug=slug.strip())
        except Adong.DoesNotExist:
            return Response({"detail": f"Unknown adong: {slug}"}, status=status.HTTP_404_NOT_FOUND)
        try:
            with transaction.atomic():
                fav = Favorite.objects.create(user=request.user, adong=adong)
        except IntegrityError:
            return Response({"detail": "Already favorited."}, status=status.HTTP_409_CONFLICT)
        return Response(FavoriteItemSerializer(build_favorite_item(fav)).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["users"], summary="Delete favorite")
@method_decorator(csrf_exempt, name="dispatch")
class FavoriteDetailView(AuthRequiredMixin, APIView):
    def delete(self, request: Request, slug: str) -> Response:
        deleted, _ = Favorite.objects.filter(user=request.user, adong__slug=slug).delete()
        if deleted == 0:
            raise NotFound({"detail": f"Favorite not found: {slug}"})
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["users"], summary="Saved candidate neighborhoods")
@method_decorator(csrf_exempt, name="dispatch")
class CandidateRegionsView(AuthRequiredMixin, APIView):
    def get(self, request: Request) -> Response:
        return Response({"max_items": MAX_CANDIDATES, "items": _load_candidate_regions(request.user)}, status=status.HTTP_200_OK)

    def put(self, request: Request) -> Response:
        items = _clean_candidates((request.data or {}).get("items"))
        saved_items = _replace_candidate_regions(request.user, items)
        return Response({"max_items": MAX_CANDIDATES, "items": saved_items}, status=status.HTTP_200_OK)


@extend_schema(tags=["users"], summary="Saved recommendation conditions")
@method_decorator(csrf_exempt, name="dispatch")
class RecommendationConditionsView(AuthRequiredMixin, APIView):
    def get(self, request: Request) -> Response:
        conditions = cache.get(_conditions_cache_key(request.user.id))
        return Response({"conditions": _clean_conditions(conditions)}, status=status.HTTP_200_OK)

    def put(self, request: Request) -> Response:
        conditions = _clean_conditions((request.data or {}).get("conditions"))
        if conditions is None:
            return Response({"conditions": "conditions is required."}, status=status.HTTP_400_BAD_REQUEST)
        cache.set(_conditions_cache_key(request.user.id), conditions, timeout=USER_CACHE_TTL_SECONDS)
        return Response({"conditions": conditions}, status=status.HTTP_200_OK)
