"""Bus admin (버스 정류장 / 버스 혼잡도).

sub-plan 4.5B 정합: BusStop PK varchar(20), adong/ldong FK 단일.
arsId → stop_number, dong FK 제거.
"""

from django.contrib import admin

from .models import BusCongestion, BusStop


@admin.register(BusStop)
class BusStopAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "stop_number", "adong", "ldong")
    list_filter = ("adong__gu",)
    search_fields = ("id", "name", "stop_number", "adong__name", "ldong__name")
    readonly_fields = ("location",)
    list_select_related = ("adong", "ldong")
    list_per_page = 50


@admin.register(BusCongestion)
class BusCongestionAdmin(admin.ModelAdmin):
    list_display = ("bus_stop", "date", "time", "congestion")
    list_filter = ("date",)
    search_fields = ("bus_stop__name", "bus_stop__stop_number")
    list_select_related = ("bus_stop",)
    list_per_page = 100
    date_hierarchy = "date"
