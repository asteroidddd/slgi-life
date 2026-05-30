from django.urls import path

from .views import (
    AdongIntroView,
    AdongLookupView,
    DashboardCacheView,
    LdongIntroView,
    LdongLookupView,
)
from .safety import CrimeZoneWmsView

app_name = "dashboard_cache"

urlpatterns = [
    path("cache", DashboardCacheView.as_view(), name="cache"),
    path("regions/adongs/lookup", AdongLookupView.as_view(), name="adong-lookup"),
    path("regions/adongs/<str:slug>/intro", AdongIntroView.as_view(), name="adong-intro"),
    path("regions/ldongs/lookup", LdongLookupView.as_view(), name="ldong-lookup"),
    path("regions/ldongs/<str:slug>/intro", LdongIntroView.as_view(), name="ldong-intro"),
    path("safety/crime-zone", CrimeZoneWmsView.as_view(), name="safety-crime-zone"),
]
