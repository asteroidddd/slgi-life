"""Standalone 스크립트가 Django ORM을 쓰기 위한 공통 setup helper.

사용 예:
    from _django import setup
    setup()
    from apps.public_data.regions.models import Adong  # noqa: E402
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def setup() -> None:
    """Django settings 로드. 모듈 import 전에 반드시 호출."""

    # backend/scripts/_django.py → backend/ 를 sys.path 루트에 추가
    backend_root = Path(__file__).resolve().parent.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

    import django  # 지연 import — sys.path 설정 후에야 의미가 있음

    django.setup()


def require_env(name: str, hint: str | None = None) -> str:
    """환경 변수 필수 체크. 없으면 친절한 안내 후 SystemExit(1)."""

    value = os.environ.get(name, "").strip()
    if not value:
        msg = f"[ERROR] 환경 변수 {name} 가 설정되지 않았습니다."
        if hint:
            msg += f"\n        {hint}"
        msg += "\n        backend/scripts/README.md 의 '필요 키' 항목을 확인하세요."
        print(msg, file=sys.stderr)
        raise SystemExit(1)
    return value
