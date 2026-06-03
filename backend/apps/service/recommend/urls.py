from django.urls import path

from apps.service.recommend.views import RecommendationRegionsView

app_name = "recommend"

urlpatterns = [
    path("recommend/regions", RecommendationRegionsView.as_view(), name="recommend-regions"),
]
