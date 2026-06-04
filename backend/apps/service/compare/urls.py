from django.urls import path

from .views import NeighborhoodCommuteTimeView, NeighborhoodCompareView

app_name = "compare_service"

urlpatterns = [
    path("compare/neighborhoods", NeighborhoodCompareView.as_view(), name="neighborhoods"),
    path("compare/commute-time", NeighborhoodCommuteTimeView.as_view(), name="commute-time"),
]
