"""
rent_deal 앱 URL.

마운트 위치: config/urls.py 의 path("api/", include("apps.public_data.rent_deal.urls"))
즉, 여기서는 'transactions/...' 형태로 작성.

이동 이력:
- sub-plan 2H: `apps.public_data.realestate.urls` → `apps.public_data.rent_deal.urls`로 이동.
"""

from django.urls import path

from .views import TransactionsBboxView

app_name = "rent_deal"

urlpatterns = [
    # GET /api/transactions/bbox?bbox=lng1,lat1,lng2,lat2&...
    path("transactions/bbox", TransactionsBboxView.as_view(), name="transactions-bbox"),
]
