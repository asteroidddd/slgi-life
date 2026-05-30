from django.urls import path

from .views import (
    RentDealCacheView,
    RentDealGridSummaryView,
    RentDealGuCacheView,
    RentDealGuCodesView,
    RentDealLdongSummaryView,
    RentDealListingAnalysisView,
    RentDealConversionRateView,
    RentDealDetailView,
    RentDealMatchCountsView,
)

app_name = "rent_deal_service"

urlpatterns = [
    path("rent-deals/cache", RentDealCacheView.as_view(), name="rent-deal-cache"),
    path("rent-deals/cache/gus", RentDealGuCodesView.as_view(), name="rent-deal-cache-gus"),
    path("rent-deals/cache/gus/<str:gu_code>.tsv.gz", RentDealGuCacheView.as_view(), name="rent-deal-cache-gu"),
    path("rent-deals/summary/ldongs", RentDealLdongSummaryView.as_view(), name="rent-deal-ldong-summary"),
    path("rent-deals/summary/grids", RentDealGridSummaryView.as_view(), name="rent-deal-grid-summary"),
    path("rent-deals/match-counts", RentDealMatchCountsView.as_view(), name="rent-deal-match-counts"),
    path("rent-deals/listing-analysis", RentDealListingAnalysisView.as_view(), name="rent-deal-listing-analysis"),
    path("rent-deals/conversion-rate", RentDealConversionRateView.as_view(), name="rent-deal-conversion-rate"),
    path("rent-deals/<str:deal_id>", RentDealDetailView.as_view(), name="rent-deal-detail"),
]
