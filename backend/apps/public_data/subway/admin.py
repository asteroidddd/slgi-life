"""Subway admin (지하철역 / 가까운 역 캐시 / 지하철 혼잡도).

sub-plan 4.5B 정합: SubwayStation PK varchar(20), adong/ldong FK 단일.
external_id 제거, created_at/updated_at 제거.
"""

from django.contrib import admin

from .models import (
    NearestSubwayAdong,
    NearestSubwayLdong,
    SubwayCongestion,
    SubwayStation,
)


@admin.register(SubwayStation)
class SubwayStationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "line", "adong", "ldong")
    list_filter = ("line",)
    search_fields = ("id", "name", "line")
    readonly_fields = ("location",)
    list_select_related = ("adong", "ldong")
    list_per_page = 50


@admin.register(NearestSubwayAdong)
class NearestSubwayAdongAdmin(admin.ModelAdmin):
    list_display = ("adong", "rank", "station_name", "distance_m")
    list_filter = ("rank",)
    search_fields = ("adong__name", "station_name")
    list_select_related = ("adong",)
    list_per_page = 100


@admin.register(NearestSubwayLdong)
class NearestSubwayLdongAdmin(admin.ModelAdmin):
    list_display = ("ldong", "rank", "station_name", "distance_m")
    list_filter = ("rank",)
    search_fields = ("ldong__name", "station_name")
    list_select_related = ("ldong",)
    list_per_page = 100


@admin.register(SubwayCongestion)
class SubwayCongestionAdmin(admin.ModelAdmin):
    list_display = ("station", "day_type", "direction", "express_yn", "time", "congestion")
    list_filter = ("day_type", "direction", "express_yn")
    search_fields = ("station__name", "station__line")
    list_select_related = ("station",)
    list_per_page = 100
