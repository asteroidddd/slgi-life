"""RentDeal admin.

sub-plan 4.5B 정합:
- adong FK 제거 → ldong FK 단일.
- 컬럼명: deal_date → contract_date, build_year → construction_year.
- deal_type 영문 enum 컬럼 제거 → housing_type 한글 raw.
- external_hash / external_id / created_at 제거.
"""

from django.contrib import admin

from .models import RentDeal


@admin.register(RentDeal)
class RentDealAdmin(admin.ModelAdmin):
    list_display = (
        "contract_date",
        "housing_type",
        "ldong",
        "area_m2",
        "deposit",
        "monthly_rent",
        "jibun",
    )
    list_filter = ("housing_type", "ldong__gu")
    search_fields = ("jibun", "house_name", "ldong__name", "ldong__gu__name")
    readonly_fields = ("location",)
    list_select_related = ("ldong", "ldong__gu")
    list_per_page = 50
    date_hierarchy = "contract_date"
    fieldsets = (
        ("기본", {"fields": ("id", "ldong", "housing_type", "contract_date")}),
        (
            "계약",
            {
                "fields": (
                    "area_m2",
                    "deposit",
                    "monthly_rent",
                    "floor",
                    "construction_year",
                    "house_name",
                )
            },
        ),
        (
            "갱신",
            {
                "fields": (
                    "contract_end_date",
                    "contract_type",
                    "renewal_request_right_used",
                    "previous_deposit",
                    "previous_monthly_rent",
                )
            },
        ),
        ("위치", {"fields": ("jibun", "location")}),
    )
