from __future__ import annotations

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_agent.byok.services import (
    InvalidPassphrase,
    purge_stale_user_keys,
    save_user_key,
    status_for_user,
    unlock_user_keys,
)
from apps.ai_agent.models import UserAIAPIKey

from .common import AgentAuthMixin, error_response


@method_decorator(csrf_exempt, name="dispatch")
class AIAPIKeyView(AgentAuthMixin, APIView):
    def get(self, request):
        purge_stale_user_keys()
        return Response({
            "keys": status_for_user(request.user),
            "unlock_ttl_seconds": 1800,
            "can_use_demo": bool(request.user.is_staff or request.user.is_superuser),
        })

    def post(self, request):
        purge_stale_user_keys()
        provider = str(request.data.get("provider") or "").strip()
        api_key = str(request.data.get("api_key") or "").strip()
        passphrase = str(request.data.get("passphrase") or "")
        priority = request.data.get("priority") or 1
        if provider not in {UserAIAPIKey.PROVIDER_OPENAI, UserAIAPIKey.PROVIDER_MINDLOGIC}:
            return error_response("AI_PROVIDER_UNSUPPORTED", "Unsupported provider.", status.HTTP_400_BAD_REQUEST)
        if not api_key:
            return error_response("AI_API_KEY_REQUIRED", "api_key is required.", status.HTTP_400_BAD_REQUEST)
        if not passphrase:
            return error_response("AI_KEY_PASSPHRASE_REQUIRED", "passphrase is required.", status.HTTP_400_BAD_REQUEST)
        try:
            save_user_key(
                user=request.user,
                provider=provider,
                api_key=api_key,
                passphrase=passphrase,
                priority=int(priority),
            )
        except Exception as exc:
            return error_response("AI_API_KEY_SAVE_FAILED", str(exc), status.HTTP_400_BAD_REQUEST)
        return Response({
            "keys": status_for_user(request.user),
            "unlock_ttl_seconds": 1800,
            "can_use_demo": bool(request.user.is_staff or request.user.is_superuser),
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name="dispatch")
class AIAPIKeyUnlockView(AgentAuthMixin, APIView):
    def post(self, request):
        purge_stale_user_keys()
        passphrase = str(request.data.get("passphrase") or "")
        if not passphrase:
            return error_response("AI_KEY_PASSPHRASE_REQUIRED", "passphrase is required.", status.HTTP_400_BAD_REQUEST)
        try:
            unlocked = unlock_user_keys(user=request.user, passphrase=passphrase)
        except InvalidPassphrase:
            return error_response("AI_API_KEY_UNLOCK_FAILED", "Invalid passphrase.", status.HTTP_400_BAD_REQUEST)
        return Response({
            "unlocked": unlocked,
            "unlock_ttl_seconds": 1800,
            "keys": status_for_user(request.user),
            "can_use_demo": bool(request.user.is_staff or request.user.is_superuser),
        })


@method_decorator(csrf_exempt, name="dispatch")
class AIAPIKeyDetailView(AgentAuthMixin, APIView):
    def delete(self, request, provider: str):
        purge_stale_user_keys()
        if provider not in {UserAIAPIKey.PROVIDER_OPENAI, UserAIAPIKey.PROVIDER_MINDLOGIC}:
            return error_response("AI_PROVIDER_UNSUPPORTED", "Unsupported provider.", status.HTTP_400_BAD_REQUEST)
        UserAIAPIKey.objects.filter(user=request.user, provider=provider).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
