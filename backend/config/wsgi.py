"""WSGI 엔트리포인트 — Gunicorn/uWSGI에서 사용."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = get_wsgi_application()
