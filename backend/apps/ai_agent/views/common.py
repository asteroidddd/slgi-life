from __future__ import annotations

from django.views.decorators.csrf import csrf_exempt
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


MAX_HISTORY = 10
CONVERSATION_TTL_SECONDS = 30 * 60


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):  # type: ignore[no-untyped-def]
        return


class AgentAuthMixin:
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]


def error_response(code: str, detail: str, http_status: int) -> Response:
    return Response({"error": code, "detail": detail}, status=http_status)


def conversation_key(user_id: int, conversation_id: str) -> str:
    return f"ai-conversation:{user_id}:{conversation_id}"


def coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
