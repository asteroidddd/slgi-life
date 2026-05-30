from __future__ import annotations

from django.contrib.auth import logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.user.authentication import CsrfExemptSessionAuthentication
from apps.ai_agent.byok.services import lock_user_keys


@extend_schema(tags=["auth"], summary="Register")
@method_decorator(csrf_exempt, name="dispatch")
class RegisterView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        return Response(
            {"detail": "Kakao login is required."},
            status=status.HTTP_410_GONE,
        )


@extend_schema(tags=["auth"], summary="Login")
@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        return Response(
            {"detail": "Kakao login is required."},
            status=status.HTTP_410_GONE,
        )


@extend_schema(tags=["auth"], summary="Logout")
@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        user = request.user
        if user.is_authenticated:
            lock_user_keys(user)
        logout(request)
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)
