from __future__ import annotations

from datetime import time

from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public_data.medical.models import (
    MedicalEmergency,
    MedicalFacility,
    MedicalFacilityHours,
    MedicalFacilitySpecialty,
    MedicalHolidayCare,
)

from .serializers import MedicalFacilityDetailSerializer, MedicalFacilityListSerializer


CATEGORY_TYPES = {
    "hospital": (
        "\uc758\uc6d0",
        "\ubcd1\uc6d0",
        "\uc885\ud569\ubcd1\uc6d0",
        "\ud55c\uc758\uc6d0",
        "\ud55c\ubc29\ubcd1\uc6d0",
        "\ubcf4\uac74\uc18c",
    ),
    "dental": ("\uce58\uacfc\uc758\uc6d0", "\uce58\uacfc\ubcd1\uc6d0"),
    "pharmacy": ("\uc57d\uad6d",),
}
ALLOWED_CATEGORIES = ("hospital", "dental", "pharmacy", "emergency")
SPECIALTY_GROUP_ALL = "전체"
SPECIALTY_GROUP_GENERAL = "일반"
SPECIALTY_GROUP_GENERAL_EXCLUDED = ("기타", "한의원")
SPECIALTY_GROUP_ORDER = (
    "일반",
    "내과",
    "외과",
    "이비인후과",
    "안과",
    "피부과",
    "비뇨기과",
    "가정의학과",
    "산부인과",
    "소아과",
    "정신과",
    "성형외과",
    "신경과",
    "신경외과",
    "재활",
    "기타",
    "한의원",
)
DAY_NAME_TO_DAY_TYPE = {
    "Monday": "mon",
    "Tuesday": "tue",
    "Wednesday": "wed",
    "Thursday": "thu",
    "Friday": "fri",
    "Saturday": "sat",
    "Sunday": "sun",
}
DEFAULT_LIMIT = 500
MAX_LIMIT = 1000
DEFAULT_RADIUS_M = 1000
MAX_RADIUS_M = 5000


def _parse_csv(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for part in raw.split(","):
        item = part.strip()
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return tuple(out)


def _parse_categories(raw: str | None) -> tuple[str, ...]:
    categories = _parse_csv(raw) or ("hospital", "dental", "pharmacy", "emergency")
    invalid = [category for category in categories if category not in ALLOWED_CATEGORIES]
    if invalid:
        raise ValidationError({"category": f"unknown categories: {invalid}"})
    return categories


def _parse_specialty_groups(raw: str | None) -> tuple[str, ...]:
    return tuple(group for group in _parse_csv(raw) if group != SPECIALTY_GROUP_ALL)


def _parse_bool(raw: str | None, key: str) -> bool:
    if raw in (None, "", "false", "0", "no"):
        return False
    if raw in ("true", "1", "yes"):
        return True
    raise ValidationError({key: f"{key} must be true or false."})


def _parse_limit(raw: str | None) -> int:
    if raw in (None, ""):
        return DEFAULT_LIMIT
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValidationError({"limit": "limit must be an integer."}) from exc
    return max(1, min(value, MAX_LIMIT))


def _parse_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    try:
        min_lng, min_lat, max_lng, max_lat = [float(part.strip()) for part in raw.split(",")]
    except ValueError as exc:
        raise ValidationError({"bbox": "bbox must be minLng,minLat,maxLng,maxLat."}) from exc
    if min_lng >= max_lng or min_lat >= max_lat:
        raise ValidationError({"bbox": "bbox min values must be smaller than max values."})
    if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180 and -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValidationError({"bbox": "bbox coordinates are out of range."})
    return min_lng, min_lat, max_lng, max_lat


def _parse_point(params: dict) -> Point | None:
    lat_raw = params.get("lat")
    lng_raw = params.get("lng")
    if lat_raw in (None, "") and lng_raw in (None, ""):
        return None
    try:
        lat = float(lat_raw)
        lng = float(lng_raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"lat_lng": "lat and lng must be numbers."}) from exc
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValidationError({"lat_lng": "lat/lng coordinates are out of range."})
    return Point(lng, lat, srid=4326)


def _parse_radius(raw: str | None) -> int:
    if raw in (None, ""):
        return DEFAULT_RADIUS_M
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValidationError({"radius": "radius must be an integer meter value."}) from exc
    return max(1, min(value, MAX_RADIUS_M))


def _regular_open_now_filter() -> Q:
    now = timezone.localtime()
    day_type = DAY_NAME_TO_DAY_TYPE[now.strftime("%A")]
    current_time = now.time().replace(microsecond=0)
    return Q(hours__day_type=day_type, hours__is_closed=False) & (
        Q(hours__open_time__lte=current_time, hours__close_time__gte=current_time)
        | Q(hours__open_time__lte=current_time, hours__close_time=time(0, 0))
    )


def _holiday_open_now_filter() -> Q | None:
    today = timezone.localdate()
    if not MedicalHolidayCare.objects.filter(care_date=today).exists():
        return None
    current_time = timezone.localtime().time().replace(microsecond=0)
    return Q(holiday_cares__care_date=today, holiday_cares__is_closed=False) & (
        Q(holiday_cares__open_time__lte=current_time, holiday_cares__close_time__gte=current_time)
        | Q(holiday_cares__open_time__lte=current_time, holiday_cares__close_time=time(0, 0))
    )


def _open_now_filter() -> Q:
    return _holiday_open_now_filter() or _regular_open_now_filter()


def _category_filter(categories: tuple[str, ...]) -> Q:
    query = Q()
    for category in categories:
        if category == "emergency":
            query |= Q(emergency__isnull=False)
        else:
            query |= Q(type__in=CATEGORY_TYPES[category])
    return query


def _apply_specialty_group_filter(qs, groups: tuple[str, ...]):
    if not groups:
        return qs

    concrete_groups = [
        group for group in groups
        if group not in {SPECIALTY_GROUP_ALL, SPECIALTY_GROUP_GENERAL}
    ]
    specialty_query = Q()
    if SPECIALTY_GROUP_GENERAL in groups:
        specialty_query |= (
            ~Q(specialty_group__in=SPECIALTY_GROUP_GENERAL_EXCLUDED)
            & ~Q(specialty_group="")
        )
    if concrete_groups:
        specialty_query |= Q(specialty_group__in=concrete_groups)
    if not specialty_query:
        return qs

    matching_specialty = MedicalFacilitySpecialty.objects.filter(
        mapping__facility_id=OuterRef("pk"),
    ).filter(specialty_query)
    return qs.filter(Exists(matching_specialty))


def category_for_facility(facility: MedicalFacility) -> str:
    if bool(getattr(facility, "has_emergency", False)):
        return "emergency"
    if facility.type in CATEGORY_TYPES["pharmacy"]:
        return "pharmacy"
    if facility.type in CATEGORY_TYPES["dental"]:
        return "dental"
    return "hospital"


def _base_queryset():
    emergency_exists = MedicalEmergency.objects.filter(facility_id=OuterRef("pk"))
    return MedicalFacility.objects.annotate(has_emergency=Exists(emergency_exists)).select_related("emergency")


class MedicalFacilityListView(APIView):
    def get(self, request: Request) -> Response:
        categories = _parse_categories(request.query_params.get("category") or request.query_params.get("categories"))
        specialties = _parse_csv(request.query_params.get("specialty") or request.query_params.get("specialties"))
        specialty_groups = _parse_specialty_groups(
            request.query_params.get("specialty_group")
            or request.query_params.get("specialty_groups")
        )
        open_now = _parse_bool(request.query_params.get("open_now"), "open_now")
        limit = _parse_limit(request.query_params.get("limit"))
        bbox = _parse_bbox(request.query_params.get("bbox"))
        point = _parse_point(request.query_params)
        radius = _parse_radius(request.query_params.get("radius"))

        qs = _base_queryset().filter(_category_filter(categories)).filter(location__isnull=False)
        if specialties:
            qs = qs.filter(hira_mapping__specialties__specialty_name__in=specialties)
        qs = _apply_specialty_group_filter(qs, specialty_groups)
        if open_now:
            if "emergency" in categories:
                qs = qs.filter(Q(emergency__isnull=False) | _open_now_filter())
            else:
                qs = qs.filter(_open_now_filter())
        if bbox:
            qs = qs.filter(location__within=Polygon.from_bbox(bbox))
        if point:
            qs = qs.filter(location__distance_lte=(point, D(m=radius))).annotate(distance=Distance("location", point))
            qs = qs.order_by("distance", "name", "hpid")
        else:
            qs = qs.order_by("type", "name", "hpid")

        items = list(qs.distinct()[:limit])
        return Response(
            {
                "categories": categories,
                "specialties": specialties,
                "specialty_groups": specialty_groups,
                "open_now": open_now,
                "bbox": bbox,
                "radius": radius if point else None,
                "limit": limit,
                "count": len(items),
                "items": MedicalFacilityListSerializer(
                    items,
                    many=True,
                    context={"category_for": category_for_facility},
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class MedicalFacilityDetailView(APIView):
    def get(self, request: Request, hpid: str) -> Response:
        facility = get_object_or_404(
            _base_queryset().prefetch_related(
                Prefetch("hours", queryset=MedicalFacilityHours.objects.order_by("day_type")),
                Prefetch("holiday_cares", queryset=MedicalHolidayCare.objects.order_by("-care_date")),
                Prefetch("hira_mapping__specialties", queryset=MedicalFacilitySpecialty.objects.order_by("specialty_name")),
            ),
            hpid=hpid,
        )
        return Response(
            MedicalFacilityDetailSerializer(
                facility,
                context={"category_for": category_for_facility},
            ).data,
            status=status.HTTP_200_OK,
        )


class MedicalSpecialtyListView(APIView):
    def get(self, request: Request) -> Response:
        category = request.query_params.get("category")
        qs = MedicalFacilitySpecialty.objects.all()
        if category:
            categories = _parse_categories(category)
            qs = qs.filter(mapping__facility__in=_base_queryset().filter(_category_filter(categories)).values("hpid"))
        rows = (
            qs.values("specialty_name")
            .order_by("specialty_name")
            .distinct()
        )
        items = [row["specialty_name"] for row in rows]
        return Response({"count": len(items), "items": items}, status=status.HTTP_200_OK)


class MedicalSpecialtyGroupListView(APIView):
    def get(self, request: Request) -> Response:
        category = request.query_params.get("category")
        qs = MedicalFacilitySpecialty.objects.exclude(specialty_group__in=["", SPECIALTY_GROUP_GENERAL])
        if category:
            categories = _parse_categories(category)
            qs = qs.filter(mapping__facility__in=_base_queryset().filter(_category_filter(categories)).values("hpid"))
        rows_by_name = {
            row["specialty_group"]: row
            for row in qs.values("specialty_group")
            .annotate(
                rows=Count("id"),
                facilities=Count("mapping__facility_id", distinct=True),
            )
        }
        ordered_names = [
            name for name in SPECIALTY_GROUP_ORDER
            if name == SPECIALTY_GROUP_GENERAL or name in rows_by_name
        ]
        extra_names = sorted(set(rows_by_name) - set(SPECIALTY_GROUP_ORDER))
        items = [
            {
                "name": SPECIALTY_GROUP_GENERAL,
                "rows": None,
                "facilities": None,
                "description": "기타와 한의원을 제외한 진료과목 그룹",
            },
            *[
                {
                    "name": name,
                    "rows": rows_by_name[name]["rows"],
                    "facilities": rows_by_name[name]["facilities"],
                }
                for name in [*ordered_names, *extra_names]
                if name != SPECIALTY_GROUP_GENERAL
            ],
        ]
        return Response({"count": len(items), "items": items}, status=status.HTTP_200_OK)
