from django.urls import path

from .views import (
    RentDealListingAnalysisView,
    RentDealConversionRateView,
)

app_name = "rent_deal_service"

urlpatterns = [
    path("rent-deals/listing-analysis", RentDealListingAnalysisView.as_view(), name="rent-deal-listing-analysis"),
    path("rent-deals/conversion-rate", RentDealConversionRateView.as_view(), name="rent-deal-conversion-rate"),
]
