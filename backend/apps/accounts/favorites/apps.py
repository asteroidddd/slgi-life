from django.apps import AppConfig


class AccountsFavoritesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts.favorites"
    label = "accounts_favorites"
    verbose_name = "Accounts - Favorites"
