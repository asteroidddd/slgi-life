"""
프로젝트 URL 라우팅.
1차 라우팅은 프로젝트가 2차 라우팅은 앱이 한다.
API는 /api/ 하위. 도메인별 URL은 각 앱의 urls.py에 위임.

9단계: 사용자 명시로 allauth/카카오 비활성화. 표준 Django username/password
세션 인증만 사용. /api/auth/{register,login,logout} 및 /api/users/me 등은
apps.web.users.urls에서 한꺼번에 제공한다.
"""

from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Prometheus scrape endpoint (django-prometheus)
    path("", include("django_prometheus.urls")),
    # OpenAPI / Swagger / ReDoc
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # API 라우트
    path("api/", include("apps.service.neighborhoods.urls")),
    path("api/", include("apps.service.map.urls")),
    path("api/", include("apps.service.heatmap.urls")),
    # AI Agent endpoint: POST /api/agent/query
    path("api/", include("apps.ai_agent.urls")),
    path("api/", include("apps.web.users.urls")),
    path("api/", include("apps.public_data.rent_deal.urls")),
]
