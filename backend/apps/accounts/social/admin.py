from django.contrib import admin

from apps.accounts.social.models import SocialAccount


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "provider_user_id", "nickname", "updated_at")
    list_filter = ("provider",)
    search_fields = ("user__username", "provider_user_id", "nickname", "email")
    raw_id_fields = ("user",)
