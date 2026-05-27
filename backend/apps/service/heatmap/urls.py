from django.urls import path

from .views import HeatmapAdongScoresView, HeatmapLdongScoresView

app_name = "heatmap"

urlpatterns = [
    path("heatmap/adongs/scores", HeatmapAdongScoresView.as_view(), name="heatmap-adong-scores"),
    path("heatmap/ldongs/scores", HeatmapLdongScoresView.as_view(), name="heatmap-ldong-scores"),
]
