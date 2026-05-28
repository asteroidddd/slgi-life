from django.urls import path

from .views import SearchView, SeoulMaskGeoJsonView, TransitRouteView

app_name = "map"

urlpatterns = [
    path("search", SearchView.as_view(), name="search"),
    path("map/geojson/seoul-mask", SeoulMaskGeoJsonView.as_view(), name="geojson-seoul-mask"),
    path("map/transit-route", TransitRouteView.as_view(), name="transit-route"),
]
