"""metrics 앱 admin."""

from django.contrib import admin

from .models import GuMetric, Metric, SeoulMetric


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ("metric_code", "name", "unit", "category", "cycle", "is_generated")
    list_filter = ("category", "cycle", "is_generated")
    search_fields = ("metric_code", "name")


@admin.register(GuMetric)
class GuMetricAdmin(admin.ModelAdmin):
    list_display = ("gu", "date", "metric", "value")
    list_filter = ("date", "metric__category")
    search_fields = ("gu__gu_code", "gu__name", "metric__metric_code", "metric__name")
    list_select_related = ("gu", "metric")
    list_per_page = 100
    date_hierarchy = "date"


@admin.register(SeoulMetric)
class SeoulMetricAdmin(admin.ModelAdmin):
    list_display = ("seoul", "date", "metric", "value")
    list_filter = ("date", "metric__category")
    search_fields = ("metric__metric_code", "metric__name")
    list_select_related = ("seoul", "metric")
    list_per_page = 100
    date_hierarchy = "date"
