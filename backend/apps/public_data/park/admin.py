"""parks 앱 admin."""

from django.contrib import admin

from .models import Park, ParkAdong, ParkLdong


@admin.register(Park)
class ParkAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "area_m2")
    list_filter = ("category",)
    search_fields = ("id", "name")
    readonly_fields = ("boundary", "location")


@admin.register(ParkAdong)
class ParkAdongAdmin(admin.ModelAdmin):
    list_display = ("park", "adong")
    search_fields = ("park__name", "adong__name", "adong__gu__name")
    list_select_related = ("park", "adong")
    list_per_page = 100


@admin.register(ParkLdong)
class ParkLdongAdmin(admin.ModelAdmin):
    list_display = ("park", "ldong")
    search_fields = ("park__name", "ldong__name")
    list_select_related = ("park", "ldong")
    list_per_page = 100
