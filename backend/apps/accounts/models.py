"""
커스텀 User 모델 + Favorite (찜한 동네) 모델.

SPEC 6.6 마이페이지 — 프로필(학교/학년) + 찜한 동네 리스트.

Favorite는 사용자 도메인이 더 강하므로 accounts 앱 안에 둔다 (학부 프로젝트
규모상 community 앱을 별도로 만들 필요 없음).
"""

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    SPEC 10의 User. 카카오 로그인이 채워주는 것 외에 마이페이지에서
    표시할 학교/학년/닉네임을 직접 보관한다.
    """

    school = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="학교명 (예: '동국대학교'). 카카오 가입 후 사용자가 직접 입력.",
    )
    year = models.IntegerField(
        null=True,
        blank=True,
        help_text="학년 (1~6 정도). null = 미입력.",
    )
    nickname = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text=(
            "표시용 닉네임. 카카오 profile_nickname이 들어오거나, "
            "직접 입력. 빈 값이면 username을 그대로 노출."
        ),
    )
    address = models.CharField(max_length=255, blank=True, default="")
    home_location = gis_models.PointField(srid=4326, null=True, blank=True)
    address_geocode_status = models.CharField(
        max_length=20,
        blank=True,
        default="not_provided",
    )
    address_geocode_error = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "users"
        verbose_name = "사용자"
        verbose_name_plural = "사용자"


class Favorite(models.Model):
    """
    SPEC 10 / 6.6 — 사용자의 찜한 동네.

    한 사용자가 같은 동을 두 번 찜할 수 없도록 unique_together.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="favorites",
        on_delete=models.CASCADE,
    )
    # sub-plan 7G-B2 (F1-A): Adong → Adong FK 치환.
    # related_name 유지(`favorited_by`)는 cross-app 영향이 있을 수 있어 그대로 둔다.
    adong = models.ForeignKey(
        "regions.Adong",
        related_name="favorited_by",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_favorite"
        verbose_name = "찜한 동네"
        verbose_name_plural = "찜한 동네"
        unique_together = ("user", "adong")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} ♡ {self.adong}"
