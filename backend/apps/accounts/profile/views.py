from __future__ import annotations

from django.contrib.auth import logout
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.profile.geocoding import apply_address
from apps.accounts.profile.models import get_user_profile
from apps.accounts.profile.serializers import MePatchSerializer, MeSerializer
from apps.accounts.user.authentication import AuthRequiredMixin
from apps.public_data.univ.models import Univ


WITHDRAW_CONFIRM_TEXT = "자취맵 탈퇴"


@extend_schema(tags=["users"], summary="Current user")
@method_decorator(csrf_exempt, name="dispatch")
class MeView(AuthRequiredMixin, APIView):
    def get(self, request: Request) -> Response:
        return Response(MeSerializer(request.user).data, status=status.HTTP_200_OK)

    def patch(self, request: Request) -> Response:
        serializer = MePatchSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if "address" in serializer.validated_data:
            profile = get_user_profile(user)
            apply_address(profile, serializer.validated_data.get("address"))
            profile.save(
                update_fields=[
                    "address",
                    "home_location",
                    "address_geocode_status",
                    "address_geocode_error",
                ]
            )
        return Response(MeSerializer(user).data, status=status.HTTP_200_OK)

    def delete(self, request: Request) -> Response:
        confirm_text = str((request.data or {}).get("confirm_text") or "").strip()
        if confirm_text != WITHDRAW_CONFIRM_TEXT:
            return Response(
                {"confirm_text": "withdraw confirmation text is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        with transaction.atomic():
            logout(request)
            user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["users"], summary="University options")
class UniversityOptionsView(APIView):
    def get(self, request: Request) -> Response:
        rows = [
            {
                "id": row["id"],
                "name": row["name"],
                "school_type": row["school_type"],
            }
            for row in Univ.objects.values("id", "name", "school_type")
        ]
        schools = sorted(rows, key=lambda row: row["name"])
        return Response({"schools": schools}, status=status.HTTP_200_OK)
