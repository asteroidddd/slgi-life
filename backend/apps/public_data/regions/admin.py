"""regions 앱 admin — Phase 1에서는 raw 적재 위주라 기본 등록만."""

from django.contrib import admin

from .models import (
    AdongAdjacency,
    Gu,
    GuAdjacency,
    Ldong,
    LdongAdjacency,
    Seoul,
)


@admin.register(Seoul)
class SeoulAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "area_m2")
    readonly_fields = ("boundary", "location")


@admin.register(Gu)
class GuAdmin(admin.ModelAdmin):
    list_display = ("gu_code", "name", "area_m2")
    search_fields = ("gu_code", "name")
    readonly_fields = ("boundary", "location")


@admin.register(Ldong)
class LdongAdmin(admin.ModelAdmin):
    list_display = ("ldong_code", "name", "gu", "area_m2")
    list_filter = ("gu",)
    search_fields = ("ldong_code", "name")
    list_select_related = ("gu",)
    readonly_fields = ("boundary", "location")


@admin.register(GuAdjacency)
class GuAdjacencyAdmin(admin.ModelAdmin):
    list_display = ("gu_a", "gu_b")
    list_select_related = ("gu_a", "gu_b")


@admin.register(LdongAdjacency)
class LdongAdjacencyAdmin(admin.ModelAdmin):
    list_display = ("ldong_a", "ldong_b")
    list_select_related = ("ldong_a", "ldong_b")
    list_per_page = 100


@admin.register(AdongAdjacency)
class AdongAdjacencyAdmin(admin.ModelAdmin):
    list_display = ("adong_a", "adong_b")
    list_select_related = ("adong_a", "adong_b")
    list_per_page = 100


# LdongPopulation / AdongPopulation Admin은 sub-plan 2C에서
# `apps.public_data.populations.admin`으로 이동.
