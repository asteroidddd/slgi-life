from django.urls import path

from .views import SearchView, TransitRouteView

app_name = "map"

urlpatterns = [
    path("search", SearchView.as_view(), name="search"),
    path("map/transit-route", TransitRouteView.as_view(), name="transit-route"),
]
