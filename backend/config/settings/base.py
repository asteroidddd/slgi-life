"""
공통 Django 설정 (base).

환경별 설정은 local.py / production.py에서 이 파일을 import하여 오버라이드한다.
모든 시크릿/환경 의존 값은 .env로부터 django-environ을 통해 로드한다.
"""

import os
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Windows GeoDjango: GDAL 종속 DLL을 찾을 수 있도록 검색 경로 등록
# ---------------------------------------------------------------------------
if os.name == "nt":
    _gdal_dir = r"C:\Program Files\GDAL"
    if os.path.isdir(_gdal_dir):
        os.environ["PATH"] = _gdal_dir + os.pathsep + os.environ.get("PATH", "")
        os.environ.setdefault("PROJ_LIB", os.path.join(_gdal_dir, "projlib"))
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(_gdal_dir)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173", "http://127.0.0.1:5173"]),
)

# .env 로드 (있으면)
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-key-please-override")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# GeoDjango — GDAL/GEOS 라이브러리 경로 (macOS Homebrew 자동 탐지 보조)
# ---------------------------------------------------------------------------
# 환경 변수로 명시되어 있으면 그대로 사용. 자동 탐지 실패 시 .env에 추가.
GDAL_LIBRARY_PATH = env("GDAL_LIBRARY_PATH", default=None)
GEOS_LIBRARY_PATH = env("GEOS_LIBRARY_PATH", default=None)

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",  # GeoDjango
    # "django.contrib.sites",  # allauth 비활성화로 함께 주석 처리
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",  # OpenAPI 3 schema + Swagger UI / ReDoc
    "django_prometheus",  # /metrics — Prometheus scrape용
    # 9단계 — 사용자 명시로 카카오/allauth는 비활성화.
    # 표준 Django username/password (세션) 인증만 사용.
    # "allauth",
    # "allauth.account",
    # "allauth.socialaccount",
    # "allauth.socialaccount.providers.kakao",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.legacy.neighborhoods",
    "apps.service.map",
    "apps.service.rent_deal",
    # LLM 질의 API. 현재 모델은 없지만 URL/DRF 뷰 등록을 위해 Django 앱으로 둔다.
    "apps.ai_agent",
    "apps.public_data.regions",
    "apps.public_data.metrics",
    "apps.public_data.park",
    "apps.service.amenities",
    "apps.service.heatmap",
    "apps.public_data.populations",
    "apps.public_data.rent_deal",
    "apps.public_data.store",
    "apps.public_data.subway",
    "apps.public_data.bus",
    "apps.public_data.univ",
    "apps.public_data.library",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# SITE_ID = 1  # allauth 비활성화로 함께 주석 처리

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",  # 요청 시각 측정 — 가장 위
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS는 가능한 위쪽
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "allauth.account.middleware.AccountMiddleware",  # allauth 비활성화
    "django_prometheus.middleware.PrometheusAfterMiddleware",  # 응답 시각 측정 — 가장 아래
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — PostGIS
# ---------------------------------------------------------------------------
# DATABASE_URL=postgis://slgi:slgi@localhost:5433/slgi
DATABASES = {
    "default": env.db("DATABASE_URL"),
}
# django-environ이 postgis://를 인식하지만, ENGINE을 명시적으로 보장.
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# i18n / TZ
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        # BrowsableAPIRenderer는 local.py에서 DEBUG일 때만 추가
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ---------------------------------------------------------------------------
# OpenAPI / Swagger (drf-spectacular)
# /api/schema/                — 원본 OpenAPI 3.0 YAML
# /api/schema/swagger-ui/     — Swagger UI
# /api/schema/redoc/          — ReDoc
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "슬기로운 자취생활 API",
    "DESCRIPTION": (
        "서울 자취 입문자용 동네 대시보드 백엔드. "
        "Django + DRF + GeoDjango (PostGIS). "
        "더미 데이터 모드 — 10단계 data-pipeline 전까지 점수/리뷰/시세는 "
        "결정적 룰 기반 생성."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,  # /api/schema/ 자체는 인증 없이 노출
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "filter": True,
    },
    "TAGS": [
        {"name": "dongs", "description": "행정동 점수·요약·상세 (SPEC 6.1~6.3)"},
        {"name": "compare", "description": "동네 비교 (SPEC 6.4)"},
        {"name": "auth", "description": "회원가입 / 로그인 / 로그아웃"},
        {"name": "accounts", "description": "계정 — 인증, 프로필, 찜"},
    ],
    "CONTACT": {"name": "슬기로운 자취생활 (학부 캡스톤)"},
    "LICENSE": {"name": "Internal — academic project"},
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env("DJANGO_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Cache (django-redis, 5분 TTL — SPEC 14.3)
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,  # Redis 다운 시 캐시 무시하고 진행
        },
        "TIMEOUT": 60 * 5,  # 5분
    }
}
DJANGO_REDIS_IGNORE_EXCEPTIONS = True

# ---------------------------------------------------------------------------
# Logging — 개발 단계 기본
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.db.backends": {"level": "WARNING"},
    },
}

# ---------------------------------------------------------------------------
# 인증 — 9단계: 사용자 명시로 카카오/allauth 비활성화.
# 표준 Django username/password 세션 인증만 사용.
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# allauth 관련 설정은 모두 주석 처리 (필요 시 다시 켤 때 참고용).
# SITE_ID = 1
# ACCOUNT_EMAIL_VERIFICATION = "none"
# ACCOUNT_LOGIN_METHODS = {"username"}
# ACCOUNT_SIGNUP_FIELDS = ["username*", "password1*"]
# SOCIALACCOUNT_AUTO_SIGNUP = True
# SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
# SOCIALACCOUNT_QUERY_EMAIL = True
# SOCIALACCOUNT_PROVIDERS = {
#     "kakao": {
#         "APP": {
#             "client_id": env("KAKAO_REST_API_KEY", default=""),
#             "secret": env("KAKAO_CLIENT_SECRET", default=""),
#             "key": "",
#         },
#     }
# }
LOGIN_REDIRECT_URL = "/"
