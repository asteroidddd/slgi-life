from django.apps import AppConfig


class AccountsProfileConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts.profile"
    label = "accounts_profile"
    verbose_name = "Accounts - Profile"
