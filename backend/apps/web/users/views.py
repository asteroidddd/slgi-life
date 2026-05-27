"""
사용자 API (SPEC 6.6 마이페이지, 9 사용자).

9단계 — 사용자 명시로 카카오/allauth 비활성화.
표준 Django username/password 세션 인증만 사용.

엔드포인트:

  POST   /api/auth/register            가입 + 자동 로그인 (세션 쿠키)
  POST   /api/auth/login               로그인 (세션 쿠키)
  POST   /api/auth/logout              로그아웃

  GET    /api/users/me                 내 정보 + 가중치
  PATCH  /api/users/me                 school / year / nickname 부분 업데이트
  GET    /api/users/me/preference      현재 가중치 (정수 %)
  PUT    /api/users/me/preference      가중치 저장
  GET    /api/users/me/favorites       찜한 동네 (사용자 가중치 적용 점수)
  POST   /api/users/me/favorites       찜 추가  body: {"slug": "..."}
  DELETE /api/users/me/favorites/<slug>찜 해제

CSRF: SPA가 fetch/axios로 호출하기 쉽도록 본 9단계 인증 라우트는 모두
CSRF 면제(@method_decorator(csrf_exempt)). 세션 쿠키만으로 인증 식별.
학부 데모 수준이라는 가정. 운영 단계에서는 CSRF 토큰 또는 토큰 인증으로 교체.
"""

from __future__ import annotations

from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    9단계 — 학부 데모용. DRF SessionAuthentication은 unsafe method에 대해
    내부적으로 enforce_csrf를 호출하여 CSRF 토큰을 강제한다. csrf_exempt
    데코레이터는 CsrfViewMiddleware는 우회하지만 이 내부 enforce_csrf는
    우회하지 못한다. 본 클래스는 enforce_csrf를 no-op으로 오버라이드해
    SPA(axios withCredentials)에서 토큰 부담 없이 세션 쿠키만으로 인증.

    운영 단계에서는 CSRF 토큰 또는 Token/JWT 인증으로 교체할 것.
    """

    def enforce_csrf(self, request):  # type: ignore[no-untyped-def]
        return  # 무시

from apps.public_data.regions.models import Adong
from apps.service.preference.models import UserPreference

from .models import Favorite, User
from .serializers import (
    FavoriteItemSerializer,
    LoginSerializer,
    MePatchSerializer,
    MeSerializer,
    PreferenceWriteSerializer,
    RegisterSerializer,
    build_favorite_item,
    preference_to_floats,
    preference_to_int_percent,
)


# ---------------------------------------------------------------------------
# 인증 공통
# ---------------------------------------------------------------------------


class _AuthRequiredMixin:
    """
    9단계 사용자 API 공통 — 인증 실패 시 401 + 한국어 detail.

    DRF + SessionAuthentication 조합은 미인증 시 401이 아닌 403을 내는데
    (WWW-Authenticate 헤더 부재가 원인), 본 마이페이지 API는 프론트의
    "로그인 필요" UX를 명확히 401로 분기하기 위해 dispatch 단계에서 직접
    401을 반환하도록 오버라이드한다.

    또한 unsafe method(PATCH/PUT/POST/DELETE)에서 CSRF 토큰 강제를 피하기 위해
    CsrfExemptSessionAuthentication을 기본 인증 클래스로 사용한다.
    """

    authentication_classes = [CsrfExemptSessionAuthentication]
    UNAUTH_DETAIL = "로그인이 필요합니다."

    def dispatch(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        drf_request = self.initialize_request(request, *args, **kwargs)
        self.request = drf_request
        self.headers = self.default_response_headers
        try:
            self.initial(drf_request, *args, **kwargs)
            if not drf_request.user.is_authenticated:
                response = Response(
                    {"detail": self.UNAUTH_DETAIL},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            else:
                handler = getattr(
                    self, request.method.lower(), self.http_method_not_allowed
                )
                response = handler(drf_request, *args, **kwargs)
        except Exception as exc:
            response = self.handle_exception(exc)
        self.response = self.finalize_response(
            drf_request, response, *args, **kwargs
        )
        return self.response


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------


@extend_schema(tags=["auth"], summary="회원가입 (자동 로그인)")
@method_decorator(csrf_exempt, name="dispatch")
class RegisterView(APIView):
    """
    POST /api/auth/register
    body: {"username","password","school"?,"year"?,"nickname"?}

    성공: 201 + MeSerializer 형태 사용자 + 세션 쿠키 set
    실패: 409 (중복 username) / 400 (검증 실패)
    """

    authentication_classes: list = []  # 가입은 비인증 라우트
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            # username 중복은 409로 승격
            username_errs = errors.get("username") or []
            if any(
                "이미 사용" in str(m) or "already exists" in str(m).lower()
                for m in username_errs
            ):
                return Response(
                    {"username": "이미 사용 중인 username입니다."},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=data["username"],
                    password=data["password"],
                )
                user.school = data.get("school", "") or ""
                user.year = data.get("year")
                user.nickname = data.get("nickname", "") or ""
                user.save(update_fields=["school", "year", "nickname"])
        except IntegrityError:
            return Response(
                {"username": "이미 사용 중인 username입니다."},
                status=status.HTTP_409_CONFLICT,
            )

        # 가입 후 자동 로그인 (세션 쿠키 발급)
        login(request, user)
        return Response(
            MeSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


@extend_schema(tags=["auth"], summary="로그인 (세션 쿠키)")
@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    """
    POST /api/auth/login body: {"username","password"}

    성공: 200 + MeSerializer 사용자 + 세션 쿠키
    실패: 401 + 한국어 detail
    """

    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            return Response(
                {"detail": "아이디 또는 비밀번호가 올바르지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(
            MeSerializer(user).data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


@extend_schema(tags=["auth"], summary="로그아웃")
@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(APIView):
    """
    POST /api/auth/logout — 미인증 사용자가 호출해도 200 (idempotent).
    """

    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        logout(request)
        return Response({"detail": "로그아웃 되었습니다."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# GET / PATCH /api/users/me
# ---------------------------------------------------------------------------


@extend_schema(tags=["users"], summary="내 프로필 + 가중치")
@method_decorator(csrf_exempt, name="dispatch")
class MeView(_AuthRequiredMixin, APIView):
    """
    GET /api/users/me   — 내 정보 + 가중치
    PATCH /api/users/me — school/year/nickname 부분 업데이트
    """

    def get(self, request: Request) -> Response:
        return Response(
            MeSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request: Request) -> Response:
        serializer = MePatchSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # MeSerializer로 통일된 형태 응답
        return Response(
            MeSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# GET / PUT /api/users/me/preference
# ---------------------------------------------------------------------------


@extend_schema(tags=["users"], summary="내 가중치 (정수 % 합 100)")
@method_decorator(csrf_exempt, name="dispatch")
class PreferenceView(_AuthRequiredMixin, GenericAPIView):
    """
    GET /api/users/me/preference  — 현재 가중치 (정수 %)
    PUT /api/users/me/preference  — 정수 % (합 100±1) 저장 후 정수 % 반환
    """

    serializer_class = PreferenceWriteSerializer

    def get(self, request: Request) -> Response:
        pref = getattr(request.user, "preference", None)
        return Response(
            preference_to_int_percent(pref),
            status=status.HTTP_200_OK,
        )

    def put(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        floats = serializer.to_floats()
        pref, _ = UserPreference.objects.update_or_create(
            user=request.user,
            defaults={
                "w_rent": floats["w_rent"],
                "w_amenity": floats["w_amenity"],
                "w_transit": floats["w_transit"],
            },
        )
        return Response(
            preference_to_int_percent(pref),
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# GET / POST /api/users/me/favorites
# ---------------------------------------------------------------------------


@extend_schema(tags=["users"], summary="찜한 동네 (목록 + 추가)")
@method_decorator(csrf_exempt, name="dispatch")
class FavoritesView(_AuthRequiredMixin, APIView):
    """
    GET  /api/users/me/favorites  — 찜한 동네 (최신순, 사용자 가중치로 점수)
    POST /api/users/me/favorites  body: {"slug": "..."} — 찜 추가
        201 + 항목 / 409 (이미 찜) / 404 (slug 없음) / 400 (slug 누락)
    """

    def _user_weights(self, request: Request) -> dict[str, float]:
        pref = getattr(request.user, "preference", None)
        return preference_to_floats(pref)

    def get(self, request: Request) -> Response:
        # sub-plan 7G-B2 (F1-A): adong → adong 치환.
        # score는 CurrentAdong join(`adong__current_score`)으로 합성.
        # 결정 1A: current_adong 미존재 또는 score_rent NULL → 0 fallback (serializer 측에서 처리).
        favs = (
            Favorite.objects.filter(user=request.user)
            .select_related("adong", "adong__gu", "adong__current_score")
        )
        weights = self._user_weights(request)
        items = [build_favorite_item(f, weights) for f in favs]
        return Response(
            FavoriteItemSerializer(items, many=True).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request: Request) -> Response:
        slug = (request.data or {}).get("slug")
        if not isinstance(slug, str) or not slug.strip():
            return Response(
                {"slug": "slug 문자열이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        slug = slug.strip()

        # sub-plan 7G-B2 (F1-A): Adong → Adong + CurrentAdong join.
        try:
            adong = Adong.objects.select_related("gu", "current_score").get(slug=slug)
        except Adong.DoesNotExist:
            return Response(
                {"detail": f"찾을 수 없는 동네: {slug}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            with transaction.atomic():
                fav = Favorite.objects.create(user=request.user, adong=adong)
        except IntegrityError:
            return Response(
                {"detail": "이미 찜한 동네입니다."},
                status=status.HTTP_409_CONFLICT,
            )

        weights = self._user_weights(request)
        return Response(
            FavoriteItemSerializer(build_favorite_item(fav, weights)).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# DELETE /api/users/me/favorites/<slug>
# ---------------------------------------------------------------------------


@extend_schema(tags=["users"], summary="찜 해제 (DELETE)")
@method_decorator(csrf_exempt, name="dispatch")
class FavoriteDetailView(_AuthRequiredMixin, APIView):
    """DELETE /api/users/me/favorites/<slug> — 찜 해제. 204 또는 404."""

    def delete(self, request: Request, slug: str) -> Response:
        # sub-plan 7G-B2 (F1-A): dong__slug → adong__slug.
        deleted, _ = Favorite.objects.filter(
            user=request.user, adong__slug=slug
        ).delete()
        if deleted == 0:
            raise NotFound({"detail": f"찜 목록에 없는 동네: {slug}"})
        return Response(status=status.HTTP_204_NO_CONTENT)


