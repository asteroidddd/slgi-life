from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.profile.models import UserProfile
from apps.accounts.social.models import SocialAccount
from apps.accounts.user.models import User


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


class SocialAccountInline(admin.TabularInline):
    model = SocialAccount
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, SocialAccountInline)
    list_display = (
        "username",
        "email",
        "is_staff",
        "is_active",
    )
