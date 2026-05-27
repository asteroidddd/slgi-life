"""
neighborhoods 앱 URL.

마운트 위치: config/urls.py 의 path("api/", include("apps.service.neighborhoods.urls"))
즉, 여기서는 'adongs/...' 형태로 작성.
"""

from django.urls import path

from apps.public_data.park.views import AdongParksView
from apps.public_data.subway.views import AdongTransitCongestionView

from .match import AdongMatchCountsView, AdongMatchDetailView
from .views import (
    CompareView,
    AdongDetailView,
    AdongGeoJsonView,
    AdongExploreView,
    AdongGuMetricsSeriesView,
    AdongGuMetricsView,
    AdongPopulationView,
    AdongScoresView,
    AdongSummaryView,
    KernelScoreView,
    SchoolOptionsView,
    SeoulMaskGeoJsonView,
)

app_name = "neighborhoods"

urlpatterns = [
    path("geojson/adongs", AdongGeoJsonView.as_view(), name="geojson-adongs"),
    path("geojson/seoul-mask", SeoulMaskGeoJsonView.as_view(), name="geojson-seoul-mask"),
    path("schools/options", SchoolOptionsView.as_view(), name="school-options"),
    # GET /api/adongs/scores
    path("adongs/scores", AdongScoresView.as_view(), name="adong-scores"),
    # GET /api/adongs/match-counts — 메인 지도 자취 거래량 분포 (Phase 5)
    path("adongs/match-counts", AdongMatchCountsView.as_view(), name="adong-match-counts"),
    # GET /api/adongs/<slug>/match-detail — 동 패널 매칭 KPI (Phase 5)
    path(
        "adongs/<str:slug>/match-detail",
        AdongMatchDetailView.as_view(),
        name="adong-match-detail",
    ),
    # GET /api/adongs/<slug>/summary
    path("adongs/<str:slug>/summary", AdongSummaryView.as_view(), name="adong-summary"),
    # GET /api/adongs/<slug>/detail
    path("adongs/<str:slug>/detail", AdongDetailView.as_view(), name="adong-detail"),
    # GET /api/adongs/<slug>/explore — 자취 시세 BI 대시보드 (Phase 4.8)
    path("adongs/<str:slug>/explore", AdongExploreView.as_view(), name="adong-explore"),
    # GET /api/adongs/<slug>/population — 행정동 인구 시계열 (대시보드 Phase 2)
    path("adongs/<str:slug>/population", AdongPopulationView.as_view(), name="adong-population"),
    # GET /api/adongs/<slug>/gu-metrics — 소속 구 지표 + 서울 평균 (대시보드 Phase 2)
    path("adongs/<str:slug>/gu-metrics", AdongGuMetricsView.as_view(), name="adong-gu-metrics"),
    # GET /api/adongs/<slug>/gu-metrics/series — 구별 지표 시계열 (대시보드 Phase 4 추이)
    path(
        "adongs/<str:slug>/gu-metrics/series",
        AdongGuMetricsSeriesView.as_view(),
        name="adong-gu-metrics-series",
    ),
    # GET /api/adongs/<slug>/parks — 행정동에 매핑된 공원 목록 (대시보드 §4.4 섹션 B)
    path("adongs/<str:slug>/parks", AdongParksView.as_view(), name="adong-parks"),
    # GET /api/adongs/<slug>/transit-congestion — 시간대 혼잡도 + 동 성격 (대시보드 §4.4 C, §4.5)
    path(
        "adongs/<str:slug>/transit-congestion",
        AdongTransitCongestionView.as_view(),
        name="adong-transit-congestion",
    ),
    # GET /api/compare?slugs=A,B,C
    path("compare", CompareView.as_view(), name="compare"),
    # POST /api/score/point  (Phase 2a — 임의 지점 커널 점수, SPEC 11)
    path("score/point", KernelScoreView.as_view(), name="score-point"),
]
