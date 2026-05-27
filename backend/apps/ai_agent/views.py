from __future__ import annotations

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .agent import run_agent
from .byok.services import (
    BYOKError,
    InvalidPassphrase,
    get_unlocked_credentials,
    save_user_key,
    status_for_user,
    unlock_user_keys,
)
from .models import UserAIAPIKey


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):  # type: ignore[no-untyped-def]
        return


class AgentAuthMixin:
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]


def _error(code: str, detail: str, http_status: int) -> Response:
    return Response({"error": code, "detail": detail}, status=http_status)


@method_decorator(csrf_exempt, name="dispatch")
class AIAPIKeyView(AgentAuthMixin, APIView):
    def get(self, request):
        return Response({"keys": status_for_user(request.user), "unlock_ttl_seconds": 1800})

    def post(self, request):
        provider = str(request.data.get("provider") or "").strip()
        api_key = str(request.data.get("api_key") or "").strip()
        passphrase = str(request.data.get("passphrase") or "")
        priority = request.data.get("priority") or 1
        if provider not in {UserAIAPIKey.PROVIDER_OPENAI, UserAIAPIKey.PROVIDER_MINDLOGIC}:
            return _error("AI_PROVIDER_UNSUPPORTED", "Unsupported provider.", status.HTTP_400_BAD_REQUEST)
        if not api_key:
            return _error("AI_API_KEY_REQUIRED", "api_key is required.", status.HTTP_400_BAD_REQUEST)
        if not passphrase:
            return _error("AI_KEY_PASSPHRASE_REQUIRED", "passphrase is required.", status.HTTP_400_BAD_REQUEST)
        try:
            save_user_key(
                user=request.user,
                provider=provider,
                api_key=api_key,
                passphrase=passphrase,
                priority=int(priority),
            )
        except Exception as exc:
            return _error("AI_API_KEY_SAVE_FAILED", str(exc), status.HTTP_400_BAD_REQUEST)
        return Response({"keys": status_for_user(request.user)}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name="dispatch")
class AIAPIKeyUnlockView(AgentAuthMixin, APIView):
    def post(self, request):
        passphrase = str(request.data.get("passphrase") or "")
        if not passphrase:
            return _error("AI_KEY_PASSPHRASE_REQUIRED", "passphrase is required.", status.HTTP_400_BAD_REQUEST)
        try:
            unlocked = unlock_user_keys(user=request.user, passphrase=passphrase)
        except InvalidPassphrase:
            return _error("AI_API_KEY_UNLOCK_FAILED", "Invalid passphrase.", status.HTTP_400_BAD_REQUEST)
        return Response({"unlocked": unlocked, "unlock_ttl_seconds": 1800, "keys": status_for_user(request.user)})


@method_decorator(csrf_exempt, name="dispatch")
class AIAPIKeyDetailView(AgentAuthMixin, APIView):
    def delete(self, request, provider: str):
        if provider not in {UserAIAPIKey.PROVIDER_OPENAI, UserAIAPIKey.PROVIDER_MINDLOGIC}:
            return _error("AI_PROVIDER_UNSUPPORTED", "Unsupported provider.", status.HTTP_400_BAD_REQUEST)
        UserAIAPIKey.objects.filter(user=request.user, provider=provider).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def agent_query(request):
    question = str(request.data.get("question") or "").strip()
    if not question:
        return _error("AI_QUESTION_REQUIRED", "question is required.", status.HTTP_400_BAD_REQUEST)
    if len(question) > 500:
        return _error("AI_QUESTION_TOO_LONG", "question must be 500 characters or fewer.", status.HTTP_400_BAD_REQUEST)

    try:
        credentials = get_unlocked_credentials(request.user)
    except BYOKError as exc:
        return _error(exc.code, str(exc), status.HTTP_401_UNAUTHORIZED)

    failures = []
    for credential in credentials:
        try:
            result = run_agent(
                question,
                llm_credentials={
                    "provider": credential.provider,
                    "api_key": credential.api_key,
                    "base_url": credential.base_url,
                },
            )
            visualizations = result.get("visualizations", [])
            if not visualizations:
                viz = result.get("visualization", {})
                if viz and viz.get("type", "none") != "none":
                    visualizations = [viz]
            return Response(
                {
                    "answer": result.get("answer", ""),
                    "query_type": result.get("query_type", "none"),
                    "route": result.get("route", "direct"),
                    "neighborhoods": result.get("neighborhoods", []),
                    "visualizations": visualizations,
                    "elapsed_sec": result.get("elapsed_sec", 0),
                    "provider": {
                        "used_provider": credential.provider,
                        "fallback_used": bool(failures),
                        "failed_provider": failures[-1]["provider"] if failures else None,
                        "fallback_reason": failures[-1]["reason"] if failures else "",
                    },
                }
            )
        except Exception as exc:
            failures.append({"provider": credential.provider, "reason": type(exc).__name__})

    return Response(
        {
            "error": "AI_PROVIDER_FAILED",
            "detail": "All configured AI providers failed.",
            "provider_failures": failures,
        },
        status=status.HTTP_502_BAD_GATEWAY,
    )
