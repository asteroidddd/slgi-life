from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from django.contrib.auth import authenticate, login, logout
from django.contrib.gis.geos import Point
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public_data.regions.models import Adong

from .models import Favorite, User
from .serializers import (
    FavoriteItemSerializer,
    LoginSerializer,
    MePatchSerializer,
    MeSerializer,
    RegisterSerializer,
    build_favorite_item,
)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):  # type: ignore[no-untyped-def]
        return


class _AuthRequiredMixin:
    authentication_classes = [CsrfExemptSessionAuthentication]
    UNAUTH_DETAIL = "Login is required."

    def dispatch(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        drf_request = self.initialize_request(request, *args, **kwargs)
        self.request = drf_request
        self.headers = self.default_response_headers
        try:
            self.initial(drf_request, *args, **kwargs)
            if not drf_request.user.is_authenticated:
                response = Response({"detail": self.UNAUTH_DETAIL}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
                response = handler(drf_request, *args, **kwargs)
        except Exception as exc:
            response = self.handle_exception(exc)
        self.response = self.finalize_response(drf_request, response, *args, **kwargs)
        return self.response


def _geocode_address(address: str) -> tuple[Point | None, str, str]:
    query = address.strip()
    if not query:
        return None, "not_provided", ""
    key = os.environ.get("V_WORLD_API_KEY", "").strip()
    if not key:
        return None, "failed", "V_WORLD_API_KEY is not configured."
    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": "1",
        "page": "1",
        "query": query,
        "type": "address",
        "category": "road",
        "format": "json",
        "errorformat": "json",
        "key": key,
    }
    try:
        req = UrlRequest(
            f"https://api.vworld.kr/req/search?{urlencode(params)}",
            headers={"User-Agent": "capston-user-address/0.1"},
        )
        with urlopen(req, timeout=4) as res:
            payload = json.loads(res.read().decode("utf-8", errors="replace"))
        response = payload.get("response") or {}
        if response.get("status") != "OK":
            return None, "failed", str(response.get("error") or "address not found")[:255]
        items = ((response.get("result") or {}).get("items") or [])
        if isinstance(items, dict):
            items = [items]
        point = (items[0].get("point") if items else {}) or {}
        lng = float(point.get("x"))
        lat = float(point.get("y"))
        return Point(lng, lat, srid=4326), "success", ""
    except Exception as exc:
        return None, "failed", str(exc)[:255]


def _apply_address(user: User, address: str | None) -> None:
    cleaned = (address or "").strip()
    user.address = cleaned
    point, status_value, error = _geocode_address(cleaned)
    user.home_location = point
    user.address_geocode_status = status_value
    user.address_geocode_error = error


@extend_schema(tags=["auth"], summary="Register")
@method_decorator(csrf_exempt, name="dispatch")
class RegisterView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            if "username" in errors:
                return Response(errors, status=status.HTTP_409_CONFLICT)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            with transaction.atomic():
                user = User.objects.create_user(username=data["username"], password=data["password"])
                user.school = data.get("school") or ""
                user.year = data.get("year")
                user.nickname = data.get("nickname") or ""
                _apply_address(user, data.get("address"))
                user.save(
                    update_fields=[
                        "school",
                        "year",
                        "nickname",
                        "address",
                        "home_location",
                        "address_geocode_status",
                        "address_geocode_error",
                    ]
                )
        except IntegrityError:
            return Response({"username": "username already exists."}, status=status.HTTP_409_CONFLICT)

        login(request, user)
        return Response(MeSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["auth"], summary="Login")
@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            return Response({"detail": "Invalid username or password."}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        return Response(MeSerializer(user).data, status=status.HTTP_200_OK)


@extend_schema(tags=["auth"], summary="Logout")
@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        logout(request)
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)


@extend_schema(tags=["users"], summary="Current user")
@method_decorator(csrf_exempt, name="dispatch")
class MeView(_AuthRequiredMixin, APIView):
    def get(self, request: Request) -> Response:
        return Response(MeSerializer(request.user).data, status=status.HTTP_200_OK)

    def patch(self, request: Request) -> Response:
        serializer = MePatchSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if "address" in serializer.validated_data:
            _apply_address(user, serializer.validated_data.get("address"))
            user.save(update_fields=["address", "home_location", "address_geocode_status", "address_geocode_error"])
        return Response(MeSerializer(user).data, status=status.HTTP_200_OK)


@extend_schema(tags=["users"], summary="Favorites")
@method_decorator(csrf_exempt, name="dispatch")
class FavoritesView(_AuthRequiredMixin, APIView):
    def get(self, request: Request) -> Response:
        favs = Favorite.objects.filter(user=request.user).select_related(
            "adong", "adong__gu", "adong__current_score"
        )
        items = [build_favorite_item(f) for f in favs]
        return Response(FavoriteItemSerializer(items, many=True).data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        slug = (request.data or {}).get("slug")
        if not isinstance(slug, str) or not slug.strip():
            return Response({"slug": "slug is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            adong = Adong.objects.select_related("gu", "current_score").get(slug=slug.strip())
        except Adong.DoesNotExist:
            return Response({"detail": f"Unknown adong: {slug}"}, status=status.HTTP_404_NOT_FOUND)
        try:
            with transaction.atomic():
                fav = Favorite.objects.create(user=request.user, adong=adong)
        except IntegrityError:
            return Response({"detail": "Already favorited."}, status=status.HTTP_409_CONFLICT)
        return Response(FavoriteItemSerializer(build_favorite_item(fav)).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["users"], summary="Delete favorite")
@method_decorator(csrf_exempt, name="dispatch")
class FavoriteDetailView(_AuthRequiredMixin, APIView):
    def delete(self, request: Request, slug: str) -> Response:
        deleted, _ = Favorite.objects.filter(user=request.user, adong__slug=slug).delete()
        if deleted == 0:
            raise NotFound({"detail": f"Favorite not found: {slug}"})
        return Response(status=status.HTTP_204_NO_CONTENT)
