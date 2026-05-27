"""로컬 개발용 설정. base를 확장."""

from .base import *  # noqa: F401, F403
from .base import REST_FRAMEWORK

DEBUG = True
INTERNAL_IPS = ["127.0.0.1"]

# DRF Browsable API는 개발 시에만 활성화 (브라우저에서 응답 보기 편함)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
