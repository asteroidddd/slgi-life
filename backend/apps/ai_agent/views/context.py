from __future__ import annotations

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.ai_agent.models import UserAIContextPreference

from .common import AgentAuthMixin, coerce_bool


def get_context_preference(user) -> UserAIContextPreference:
    preference, _ = UserAIContextPreference.objects.get_or_create(user=user)
    return preference


def serialize_context_preference(user, preference: UserAIContextPreference) -> dict:
    return {
        "share_school_with_ai": preference.share_school_with_ai,
        "share_home_location_with_ai": preference.share_home_location_with_ai,
        "school_available": bool(getattr(user, "school", "")),
        "home_location_available": bool(getattr(user, "home_location", None)),
    }


def build_user_context(user) -> dict:
    preference = get_context_preference(user)
    context: dict = {}
    school = str(getattr(user, "school", "") or "").strip()
    if preference.share_school_with_ai and school:
        context["school"] = school

    home_location = getattr(user, "home_location", None)
    if preference.share_home_location_with_ai and home_location:
        context["home_location"] = {
            "lat": float(home_location.y),
            "lng": float(home_location.x),
        }
    return context


@method_decorator(csrf_exempt, name="dispatch")
class AIContextPreferenceView(AgentAuthMixin, APIView):
    def get(self, request):
        preference = get_context_preference(request.user)
        return Response(serialize_context_preference(request.user, preference))

    def patch(self, request):
        preference = get_context_preference(request.user)
        if "share_school_with_ai" in request.data:
            preference.share_school_with_ai = coerce_bool(request.data.get("share_school_with_ai"))
        if "share_home_location_with_ai" in request.data:
            preference.share_home_location_with_ai = coerce_bool(request.data.get("share_home_location_with_ai"))
        preference.save(update_fields=["share_school_with_ai", "share_home_location_with_ai", "updated_at"])
        return Response(serialize_context_preference(request.user, preference))
