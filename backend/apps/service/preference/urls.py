"""
preference 앱 URL.

마운트 위치: config/urls.py 의 path("api/", include("apps.service.preference.urls"))
즉, 여기서는 'preference/...' 형태로 작성.
"""

from django.urls import path

from .views import PreferencePairsView, PreferenceSubmitView

app_name = "preference"

urlpatterns = [
    # GET /api/preference/pairs?count=5
    path("preference/pairs", PreferencePairsView.as_view(), name="preference-pairs"),
    # POST /api/preference/submit
    path("preference/submit", PreferenceSubmitView.as_view(), name="preference-submit"),
]
