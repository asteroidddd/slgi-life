"""프로덕션용 설정. base를 확장."""

from .base import *  # noqa: F401, F403
from .base import env

DEBUG = False

# 프로덕션 ALLOWED_HOSTS는 반드시 env에서.
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# 보안 헤더 (배포 시점에 reverse proxy 설정과 함께 조정)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
