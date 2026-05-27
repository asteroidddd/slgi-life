"""ASGI 엔트리포인트 — Uvicorn/Daphne 등 사용 시."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = get_asgi_application()
