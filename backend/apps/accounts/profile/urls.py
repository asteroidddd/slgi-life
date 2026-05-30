from django.urls import path

from apps.accounts.profile.views import MeView, UniversityOptionsView

urlpatterns = [
    path("users/me", MeView.as_view(), name="me"),
    path("users/universities", UniversityOptionsView.as_view(), name="universities"),
]
