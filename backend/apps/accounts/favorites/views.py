from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.favorites.models import Favorite
from apps.accounts.favorites.serializers import FavoriteItemSerializer, build_favorite_item
from apps.accounts.user.authentication import AuthRequiredMixin
from apps.public_data.regions.models import Adong


@extend_schema(tags=["users"], summary="Favorites")
@method_decorator(csrf_exempt, name="dispatch")
class FavoritesView(AuthRequiredMixin, APIView):
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
class FavoriteDetailView(AuthRequiredMixin, APIView):
    def delete(self, request: Request, slug: str) -> Response:
        deleted, _ = Favorite.objects.filter(user=request.user, adong__slug=slug).delete()
        if deleted == 0:
            raise NotFound({"detail": f"Favorite not found: {slug}"})
        return Response(status=status.HTTP_204_NO_CONTENT)
