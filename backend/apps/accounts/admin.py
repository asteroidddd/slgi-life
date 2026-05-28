from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Favorite, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    기본 UserAdmin + 마이페이지용 추가 필드 (school / year / nickname).
    """

    fieldsets = UserAdmin.fieldsets + (
        ("마이페이지", {"fields": ("nickname", "school", "year")}),
    )
    list_display = (
        "username",
        "nickname",
        "school",
        "year",
        "is_staff",
        "is_active",
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "adong", "created_at")
    list_select_related = ("user", "adong")
    search_fields = ("user__username", "adong__slug", "adong__name")
    autocomplete_fields = ()
    raw_id_fields = ("user", "adong")
