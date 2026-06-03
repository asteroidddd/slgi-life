from django.contrib import admin

from apps.service.recommend.models import AdongUnivTime, LdongUnivTime


@admin.register(AdongUnivTime)
class AdongUnivTimeAdmin(admin.ModelAdmin):
    list_display = ("adong", "univ", "time")
    search_fields = ("adong__name", "adong__gu__name", "univ__name")
    list_filter = ("time",)


@admin.register(LdongUnivTime)
class LdongUnivTimeAdmin(admin.ModelAdmin):
    list_display = ("ldong", "univ", "time")
    search_fields = ("ldong__name", "ldong__gu__name", "univ__name")
    list_filter = ("time",)
