from django.urls import path

from .views import AmenityBboxView

app_name = "amenities"

urlpatterns = [
    path("amenities/bbox", AmenityBboxView.as_view(), name="amenities-bbox"),
]
