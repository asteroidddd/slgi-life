from django.contrib import admin

from apps.accounts.profile.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "nickname", "school", "year", "address_geocode_status")
    search_fields = ("user__username", "nickname", "school", "address")
    raw_id_fields = ("user",)
