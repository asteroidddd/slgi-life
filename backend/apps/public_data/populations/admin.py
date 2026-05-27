"""populations 앱 admin — sub-plan 2C에서 regions에서 이동."""

from django.contrib import admin

from .models import AdongPopulation, LdongPopulation


@admin.register(LdongPopulation)
class LdongPopulationAdmin(admin.ModelAdmin):
    list_display = ("ldong", "date", "total_population", "household_count")
    list_filter = ("date",)
    search_fields = ("ldong__ldong_code", "ldong__name")
    list_select_related = ("ldong",)
    list_per_page = 100
    date_hierarchy = "date"


@admin.register(AdongPopulation)
class AdongPopulationAdmin(admin.ModelAdmin):
    list_display = ("adong", "date", "total_population", "household_count")
    list_filter = ("date",)
    search_fields = ("adong__name", "adong__gu__name")
    list_select_related = ("adong",)
    list_per_page = 100
    date_hierarchy = "date"
