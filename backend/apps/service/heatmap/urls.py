from django.urls import path

from .views import HeatmapAdongGeoJsonView, HeatmapAdongScoresView, HeatmapLdongGeoJsonView, HeatmapLdongScoresView

app_name = "heatmap"

urlpatterns = [
    path("heatmap/geojson/adongs", HeatmapAdongGeoJsonView.as_view(), name="heatmap-geojson-adongs"),
    path("heatmap/geojson/ldongs", HeatmapLdongGeoJsonView.as_view(), name="heatmap-geojson-ldongs"),
    path("heatmap/adongs/scores", HeatmapAdongScoresView.as_view(), name="heatmap-adong-scores"),
    path("heatmap/ldongs/scores", HeatmapLdongScoresView.as_view(), name="heatmap-ldong-scores"),
]
