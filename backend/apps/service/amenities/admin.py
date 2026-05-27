"""
Amenity admin.

Sub-plan 2J 재구성:
- dong FK 제거 (AmenityAdong/AmenityLdong N:M으로 분리)
- geom → location, external_id → source_id, source → source_table
- AmenityAdong / AmenityLdong admin은 단계 3에서 추가 예정 (현재 미등록)

Sub-plan 4.5C: created_at/updated_at 컬럼 제거 (schema.dbml 정본 정합).

PointField는 GISModelAdmin 위젯이 무겁기 때문에, list 화면은 평범한
ModelAdmin으로 유지하고 location은 readonly text로 표시한다.
"""

from django.contrib import admin

from .models import Amenity


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("category", "name", "source_table", "source_id")
    list_filter = ("category", "source_table")
    search_fields = ("name", "source_id")
    readonly_fields = ("location",)
    list_per_page = 50
    fieldsets = (
        ("기본", {"fields": ("category", "name")}),
        ("출처", {"fields": ("source_table", "source_id")}),
        ("위치 (read-only)", {"fields": ("location",)}),
    )
