from django.urls import path

from .views import (
    RentDealCacheView,
    RentDealConversionRateView,
    RentDealDetailView,
    RentDealMatchCountsView,
)

app_name = "rent_deal_service"

urlpatterns = [
    path("rent-deals/cache", RentDealCacheView.as_view(), name="rent-deal-cache"),
    path("rent-deals/match-counts", RentDealMatchCountsView.as_view(), name="rent-deal-match-counts"),
    path("rent-deals/conversion-rate", RentDealConversionRateView.as_view(), name="rent-deal-conversion-rate"),
    path("rent-deals/<str:deal_id>", RentDealDetailView.as_view(), name="rent-deal-detail"),
]
