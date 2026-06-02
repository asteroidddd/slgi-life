from __future__ import annotations

import os
import uuid

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.ai_agent.byok.services import BYOKError, ProviderCredential, get_unlocked_credentials, purge_stale_user_keys
from apps.ai_agent.models import UserAIAPIKey
from apps.ai_agent.runtime.agent import run_agent

from .common import (
    CONVERSATION_TTL_SECONDS,
    MAX_HISTORY,
    CsrfExemptSessionAuthentication,
    conversation_key,
    error_response,
)
from .context import build_user_context


PUBLIC_AI_ENV = "AI_AGENT_PUBLIC_MODE"


def public_ai_mode_enabled() -> bool:
    value = os.environ.get(PUBLIC_AI_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"} and bool(os.environ.get("AI_AGENT_OPENAI_API_KEY"))


class AgentQueryPermission(BasePermission):
    def has_permission(self, request, view):  # type: ignore[no-untyped-def]
        if public_ai_mode_enabled():
            return True
        return bool(request.user and request.user.is_authenticated)


def public_openai_credentials() -> list[ProviderCredential]:
    api_key = os.environ.get("AI_AGENT_OPENAI_API_KEY", "").strip()
    if not api_key:
        return []
    return [
        ProviderCredential(
            provider=UserAIAPIKey.PROVIDER_OPENAI,
            api_key=api_key,
            base_url=os.environ.get("AI_AGENT_OPENAI_BASE_URL") or None,
        )
    ]

def build_memory_items(result: dict, visualizations: list) -> list[dict]:
    items: list[dict] = []

    for neighborhood in result.get("neighborhoods", []) or []:
        gu_name = str(neighborhood.get("gu_name", "")).strip()
        ldong_name = str(neighborhood.get("ldong_name", "")).strip()
        label = f"{gu_name} {ldong_name}".strip()
        if label:
            items.append({
                "kind": "neighborhood",
                "label": label,
                "data": neighborhood,
            })

    for visualization in visualizations or []:
        if not isinstance(visualization, dict):
            continue
        for row in visualization.get("data", []) or []:
            if not isinstance(row, dict):
                continue
            label = str(row.get("label") or "").strip()
            if not label:
                continue
            items.append({
                "kind": "result_row",
                "label": label,
                "source": visualization.get("title", ""),
                "visualization_type": visualization.get("type", ""),
                "data": {
                    "value": row.get("value"),
                    "lat": row.get("lat"),
                    "lng": row.get("lng"),
                    "columns": row.get("columns") or {},
                },
            })

    return items[:30]

def demo_agent_response() -> dict:
    return {
        "conversation_id": str(uuid.uuid4()),
        "answer": "\ud14c\uc2a4\ud2b8 \uc751\ub2f5\uc785\ub2c8\ub2e4. \uc2e4\uc81c AI\uc640 DB\ub97c \ud638\ucd9c\ud558\uc9c0 \uc54a\uace0 \ud654\uba74 \ub80c\ub354\ub9c1\uc744 \ud655\uc778\ud569\ub2c8\ub2e4.",
        "query_type": "demo",
        "route": "demo",
        "neighborhoods": [
            {
                "name": "\uc2e0\ub9bc\ub3d9",
                "gu": "\uad00\uc545\uad6c",
                "score": 86.2,
                "one_liner": "\uc6d4\uc138 \ubd80\ub2f4\uc774 \ub0ae\uace0 \uad50\ud1b5 \uc120\ud0dd\uc9c0\uac00 \ub9ce\uc740 \uc790\ucde8 \ud6c4\ubcf4\uc9c0\uc785\ub2c8\ub2e4.",
                "data_summary": "\ucd5c\uadfc \uc6d4\uc138 \uc218\uc900\uacfc \ubc84\uc2a4 \uc811\uadfc\uc131, \uc0dd\ud65c\uc2dc\uc124 \ubc00\ub3c4\ub97c \ud568\uaed8 \ubcf8 \uc0d8\ud50c\uc785\ub2c8\ub2e4.",
            },
            {
                "name": "\uad6c\ub85c\ub3d9",
                "gu": "\uad6c\ub85c\uad6c",
                "score": 82.7,
                "one_liner": "\ube44\uc6a9 \ub300\ube44 \uc774\ub3d9 \ud3b8\uc758\uac00 \uc88b\uc544 \uc2e4\uc18d\ud615 \uc120\ud0dd\uc9c0\ub85c \ubcfc \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
                "data_summary": "\uc6d4\uc138\ub294 \ub0ae\uc740 \ud3b8\uc774\uace0 \uc9c0\ud558\ucca0\uacfc \ubc84\uc2a4 \uc811\uadfc\uc131\uc774 \uc548\uc815\uc801\uc778 \uc0d8\ud50c\uc785\ub2c8\ub2e4.",
            },
            {
                "name": "\ubd09\ucc9c\ub3d9",
                "gu": "\uad00\uc545\uad6c",
                "score": 79.4,
                "one_liner": "\ub300\ud559\uac00\uc640 \uc0dd\ud65c\uc2dc\uc124 \uc811\uadfc\uc131\uc774 \uc88b\uc544 \ucd08\ubc18 \uc815\ucc29\uc5d0 \ubb34\ub09c\ud569\ub2c8\ub2e4.",
                "data_summary": "\ud3b8\uc758\uc2dc\uc124, \ub300\uc911\uad50\ud1b5, \uc6d4\uc138 \uc870\uac74\uc744 \uc11e\uc5b4 \ubcf4\uc5ec\uc8fc\ub294 \uc0d8\ud50c\uc785\ub2c8\ub2e4.",
            },
        ],
        "visualizations": [
            {
                "type": "bar",
                "title": "\ucd94\ucc9c \ub3d9\ub124 \uc885\ud569 \uc810\uc218",
                "unit": "\uc810",
                "data": [
                    {"label": "\uc2e0\ub9bc\ub3d9", "value": 86.2},
                    {"label": "\uad6c\ub85c\ub3d9", "value": 82.7},
                    {"label": "\ubd09\ucc9c\ub3d9", "value": 79.4},
                    {"label": "\uc0ac\ub2f9\ub3d9", "value": 76.8},
                ],
            },
            {
                "type": "line",
                "title": "\uc6d4\uc138 \ucd94\uc774 \uc0d8\ud50c",
                "unit": "\ub9cc\uc6d0",
                "data": [
                    {"label": "2026-01", "value": 58},
                    {"label": "2026-02", "value": 60},
                    {"label": "2026-03", "value": 62},
                    {"label": "2026-04", "value": 61},
                    {"label": "2026-05", "value": 64},
                ],
            },
            {
                "type": "table",
                "title": "\ud6c4\ubcf4 \ub3d9\ub124 \ube44\uad50",
                "unit": "",
                "data": [
                    {"label": "\uc2e0\ub9bc\ub3d9", "columns": {"\uad6c": "\uad00\uc545\uad6c", "\ud3c9\uade0 \uc6d4\uc138": 62, "\uad50\ud1b5": "\uc88b\uc74c", "\uc0dd\ud65c\uc2dc\uc124": "\ub9ce\uc74c"}},
                    {"label": "\uad6c\ub85c\ub3d9", "columns": {"\uad6c": "\uad6c\ub85c\uad6c", "\ud3c9\uade0 \uc6d4\uc138": 65, "\uad50\ud1b5": "\ubcf4\ud1b5", "\uc0dd\ud65c\uc2dc\uc124": "\uc88b\uc74c"}},
                    {"label": "\ubd09\ucc9c\ub3d9", "columns": {"\uad6c": "\uad00\uc545\uad6c", "\ud3c9\uade0 \uc6d4\uc138": 59, "\uad50\ud1b5": "\uc88b\uc74c", "\uc0dd\ud65c\uc2dc\uc124": "\ubcf4\ud1b5"}},
                ],
            },
            {
                "type": "map",
                "title": "\ucd94\ucc9c \uc704\uce58 \uc0d8\ud50c",
                "unit": "",
                "data": [
                    {"label": "\uc2e0\ub9bc\ub3d9", "lat": 37.4842, "lng": 126.9297},
                    {"label": "\uad6c\ub85c\ub3d9", "lat": 37.4954, "lng": 126.8874},
                    {"label": "\ubd09\ucc9c\ub3d9", "lat": 37.4826, "lng": 126.9522},
                    {"label": "\uc88c\ud45c \uc5c6\ub294 \ud6c4\ubcf4", "lat": 0, "lng": 0},
                ],
            },
        ],
        "elapsed_sec": 0,
        "provider": {"used_provider": "demo", "fallback_used": False, "failed_provider": None, "fallback_reason": ""},
    }


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AgentQueryPermission])
def agent_query(request):
    purge_stale_user_keys()
    question = str(request.data.get("question") or "").strip()
    conversation_id = str(request.data.get("conversation_id") or "").strip()
    if not question:
        return error_response("AI_QUESTION_REQUIRED", "question is required.", status.HTTP_400_BAD_REQUEST)
    if len(question) > 500:
        return error_response("AI_QUESTION_TOO_LONG", "question must be 500 characters or fewer.", status.HTTP_400_BAD_REQUEST)
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    public_mode = public_ai_mode_enabled()
    is_authenticated = bool(request.user and request.user.is_authenticated)
    conversation_owner = request.user.id if is_authenticated else "public"
    store_key = conversation_key(conversation_owner, conversation_id)
    history = list(cache.get(store_key) or [])

    if public_mode:
        credentials = public_openai_credentials()
    else:
        try:
            credentials = get_unlocked_credentials(request.user)
        except BYOKError as exc:
            return error_response(exc.code, str(exc), status.HTTP_401_UNAUTHORIZED)
    if not credentials:
        return error_response("AI_PUBLIC_KEY_MISSING", "AI public API key is not configured.", status.HTTP_503_SERVICE_UNAVAILABLE)

    user_context = build_user_context(request.user) if is_authenticated else {}

    failures = []
    for credential in credentials:
        try:
            result = run_agent(
                question,
                history=history,
                llm_credentials={
                    "provider": credential.provider,
                    "api_key": credential.api_key,
                    "base_url": credential.base_url,
                },
                user_context=user_context,
            )
            visualizations = result.get("visualizations", [])
            if not visualizations:
                viz = result.get("visualization", {})
                if viz and viz.get("type", "none") != "none":
                    visualizations = [viz]

            updated = list(cache.get(store_key) or [])
            updated.append({
                "question": question,
                "answer": result.get("answer", ""),
                "neighborhoods": result.get("neighborhoods", []),
                "memory_items": build_memory_items(result, visualizations),
            })
            cache.set(store_key, updated[-MAX_HISTORY:], timeout=CONVERSATION_TTL_SECONDS)

            return Response({
                "conversation_id": conversation_id,
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
            })
        except Exception as exc:
            failures.append({"provider": credential.provider, "reason": type(exc).__name__})

    return Response({
        "error": "AI_PROVIDER_FAILED",
        "detail": "All configured AI providers failed.",
        "provider_failures": failures,
    }, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def demo_visualization_response(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return error_response("AI_DEMO_FORBIDDEN", "Staff permission is required.", status.HTTP_403_FORBIDDEN)
    return Response(demo_agent_response())


@api_view(["DELETE"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def clear_conversation(request, conversation_id: str):
    store_key = conversation_key(request.user.id, conversation_id)
    existed = cache.get(store_key) is not None
    cache.delete(store_key)
    return Response({"cleared": existed, "conversation_id": conversation_id})
