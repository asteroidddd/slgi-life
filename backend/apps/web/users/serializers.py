"""
users 앱 시리얼라이저 (SPEC 6.6 마이페이지, 9 사용자 API).

- RegisterSerializer: POST /api/auth/register body
- LoginSerializer: POST /api/auth/login body
- MeSerializer: GET /api/users/me 응답
- MePatchSerializer: PATCH /api/users/me body (school/year/nickname)
- FavoriteItemSerializer: GET/POST /api/users/me/favorites 응답 한 항목
- PreferenceWriteSerializer: PUT /api/users/me/preference body 검증
"""

from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.service.preference.models import UserPreference

from .models import Favorite, User


# ---------------------------------------------------------------------------
# 가중치 (preference) — float(0~1) ↔ int(0~100, 합 100) 변환
# ---------------------------------------------------------------------------


def preference_to_int_percent(pref: UserPreference | None) -> dict[str, int]:
    """
    UserPreference(float, 합 1) → 응답용 정수 %(합 100).

    pref가 None이면 default 33/33/34 반환. SPEC 6.1 첫 진입 가중치와 일관.
    largest-remainder 보정을 통해 합 100 보장.
    """
    if pref is None:
        return {"w_rent": 33, "w_amenity": 33, "w_transit": 34}

    raw = [
        ("w_rent", float(pref.w_rent) * 100.0),
        ("w_amenity", float(pref.w_amenity) * 100.0),
        ("w_transit", float(pref.w_transit) * 100.0),
    ]
    floors = [(k, int(v), v - int(v)) for k, v in raw]
    total = sum(f for _, f, _ in floors)
    deficit = 100 - total

    # 잔차 큰 컴포넌트부터 +1 분배
    if deficit > 0:
        order = sorted(range(3), key=lambda i: -floors[i][2])
        floors_list = [list(t) for t in floors]
        for i in range(deficit):
            floors_list[order[i % 3]][1] += 1
        floors = [tuple(t) for t in floors_list]
    elif deficit < 0:
        order = sorted(range(3), key=lambda i: floors[i][2])
        floors_list = [list(t) for t in floors]
        i = 0
        while deficit < 0 and i < 100:
            idx = order[i % 3]
            if floors_list[idx][1] > 0:
                floors_list[idx][1] -= 1
                deficit += 1
            i += 1
        floors = [tuple(t) for t in floors_list]

    return {k: int(v) for k, v, _ in floors}


def preference_to_floats(
    pref: UserPreference | None,
) -> dict[str, float]:
    """UserPreference → float(0~1) dict. None이면 default."""
    if pref is None:
        return {"w_rent": 0.33, "w_amenity": 0.33, "w_transit": 0.34}
    return {
        "w_rent": float(pref.w_rent),
        "w_amenity": float(pref.w_amenity),
        "w_transit": float(pref.w_transit),
    }


# ---------------------------------------------------------------------------
# /api/auth/register, /api/auth/login
# ---------------------------------------------------------------------------


class RegisterSerializer(serializers.Serializer):
    """
    POST /api/auth/register body 검증.

    필수: username, password
    선택: school, year, nickname
    """

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=4, max_length=128, write_only=True)
    school = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default=""
    )
    year = serializers.IntegerField(required=False, allow_null=True, default=None)
    nickname = serializers.CharField(
        max_length=30, required=False, allow_blank=True, default=""
    )

    def validate_username(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("username을 입력해주세요.")
        if User.objects.filter(username=value).exists():
            # 뷰에서 409로 변환됨
            raise serializers.ValidationError("이미 사용 중인 username입니다.")
        return value

    def validate_password(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("password를 입력해주세요.")
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class LoginSerializer(serializers.Serializer):
    """POST /api/auth/login body."""

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True)


# ---------------------------------------------------------------------------
# /api/users/me
# ---------------------------------------------------------------------------


class MeSerializer(serializers.ModelSerializer):
    """
    GET /api/users/me 응답.

    응답 형태:
      {
        "id": 1,
        "username": "demo",
        "nickname": "데모",
        "school": "동국대학교",
        "year": 3,
        "preference": {"w_rent": 33, "w_amenity": 33, "w_transit": 34}
      }

    nickname이 빈 문자열이면 username을 폴백으로 노출.
    """

    nickname = serializers.SerializerMethodField()
    preference = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "nickname", "school", "year", "preference")

    def get_nickname(self, obj: User) -> str:
        return obj.nickname or obj.username

    def get_preference(self, obj: User) -> dict[str, int]:
        # OneToOne — 없을 수 있음. attribute access 시 RelatedObjectDoesNotExist.
        pref = getattr(obj, "preference", None)
        return preference_to_int_percent(pref)


class MePatchSerializer(serializers.ModelSerializer):
    """
    PATCH /api/users/me — school/year/nickname 부분 업데이트.
    """

    class Meta:
        model = User
        fields = ("school", "year", "nickname")
        extra_kwargs = {
            "school": {"required": False},
            "year": {"required": False, "allow_null": True},
            "nickname": {"required": False},
        }


# ---------------------------------------------------------------------------
# /api/users/me/favorites
# ---------------------------------------------------------------------------


class FavoriteItemSerializer(serializers.Serializer):
    """
    GET /api/users/me/favorites 응답 한 항목.

    score는 호출자가 build_favorite_item에 user의 preference float를 전달하여
    계산한다. SPEC 6.6 — 사용자가 학습한 가중치 기준으로 표시.
    """

    slug = serializers.CharField()
    name = serializers.CharField()
    gu = serializers.CharField()
    score = serializers.FloatField()
    created_at = serializers.DateTimeField()


def build_favorite_item(fav: Favorite, weights: dict[str, float]) -> dict:
    """Favorite 인스턴스 + 사용자 가중치 → dict.

    sub-plan 7G-B2 (F1-A): Favorite.adong → Favorite.adong 치환.
    - score는 CurrentAdong.score_{rent,amenity,transit}로 합성.
      current_adong 미존재 또는 score_rent NULL은 결정 1A에 따라 0으로 fallback.
    - 응답 dict key set은 보존 (FavoriteItem schema lock — slug/name/gu/score/created_at).
    """
    adong = fav.adong
    current = getattr(adong, "current_score", None)
    score_rent = (current.score_rent if current is not None else 0.0) or 0.0
    score_amenity = (current.score_amenity if current is not None else 0.0) or 0.0
    score_transit = (current.score_transit if current is not None else 0.0) or 0.0
    score = round(
        score_rent * weights["w_rent"]
        + score_amenity * weights["w_amenity"]
        + score_transit * weights["w_transit"],
        2,
    )
    return {
        "slug": adong.slug,
        "name": adong.name,
        "gu": adong.gu.name,
        "score": score,
        "created_at": fav.created_at,
    }


# ---------------------------------------------------------------------------
# /api/users/me/preference (PUT body)
# ---------------------------------------------------------------------------


class PreferenceWriteSerializer(serializers.Serializer):
    """
    PUT /api/users/me/preference body 검증.

    body: {"w_rent": int, "w_amenity": int, "w_transit": int}  (각 0~100, 합 100±1)

    내부 저장 시에는 float(합 = 1)로 정규화.
    """

    w_rent = serializers.IntegerField(min_value=0, max_value=100)
    w_amenity = serializers.IntegerField(min_value=0, max_value=100)
    w_transit = serializers.IntegerField(min_value=0, max_value=100)

    def validate(self, attrs: dict) -> dict:
        total = attrs["w_rent"] + attrs["w_amenity"] + attrs["w_transit"]
        if abs(total - 100) > 1:
            raise serializers.ValidationError(
                {
                    "weights": (
                        f"가중치 합이 100이어야 합니다 (현재 {total}). 허용 오차는 ±1입니다."
                    )
                }
            )
        return attrs

    def to_floats(self) -> dict[str, float]:
        """검증된 정수 % → 합 1 float dict (저장용)."""
        d = self.validated_data
        total = float(d["w_rent"] + d["w_amenity"] + d["w_transit"]) or 100.0
        return {
            "w_rent": d["w_rent"] / total,
            "w_amenity": d["w_amenity"] / total,
            "w_transit": d["w_transit"] / total,
        }


# 기존 이름 호환 alias (다른 모듈이 import 중이면 안전)
PreferencePatchSerializer = PreferenceWriteSerializer
