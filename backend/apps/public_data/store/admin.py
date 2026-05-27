"""Store / BusinessCategory / KsciCategory admin.

sub-plan 4.5B 정합: Store dong FK 제거 → adong FK 단일.
"""

from django.contrib import admin

from .models import BusinessCategory, KsciCategory, Store


@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "subcategory_code",
        "subcategory_name",
        "middle_category_name",
        "main_category_name",
    )
    search_fields = (
        "subcategory_code",
        "subcategory_name",
        "middle_category_name",
        "main_category_name",
    )
    list_per_page = 100


@admin.register(KsciCategory)
class KsciCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "ksci_code",
        "subcategory_name",
        "middle_category_name",
        "main_category_name",
    )
    search_fields = ("ksci_code", "subcategory_name", "main_category_name")
    list_per_page = 100


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "branch_name", "category", "adong", "ldong")
    list_filter = ("category__main_category_name",)
    search_fields = ("id", "name", "branch_name", "address")
    list_select_related = ("category", "ksci", "adong", "ldong")
    readonly_fields = ("location",)
    list_per_page = 50
