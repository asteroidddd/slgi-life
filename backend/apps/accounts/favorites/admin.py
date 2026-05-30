from django.contrib import admin

from apps.accounts.favorites.models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "adong", "created_at")
    list_select_related = ("user", "adong")
    search_fields = ("user__username", "adong__slug", "adong__name")
    raw_id_fields = ("user", "adong")
