"""
선호 학습 결과를 사용자별로 저장하는 모델 (SPEC 10).

7단계까지는 무상태 API였다. 9단계부터는 인증된 사용자가 학습한 가중치를
이 테이블에 저장해 마이페이지/메인 지도 첫 진입 시 복원할 수 있다.

라이프사이클:
- POST /api/preference/submit — 비인증이면 그냥 결과만 반환 (저장 안 함, 7단계와 동일)
- PATCH /api/users/me/preference — 인증된 사용자가 직접 가중치 저장
- GET  /api/users/me — preference 필드에 현재 값 동봉
"""

from django.conf import settings
from django.db import models


class UserPreference(models.Model):
    """
    한 사용자당 1개 (OneToOne). 가중치 합 = 1.0 (정규화된 float).

    응답에서는 정수 % 변환 (× 100, 합 100)하여 노출.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="preference",
        on_delete=models.CASCADE,
    )
    w_rent = models.FloatField(default=0.33)
    w_amenity = models.FloatField(default=0.33)
    w_transit = models.FloatField(default=0.34)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_preference"
        verbose_name = "사용자 가중치"
        verbose_name_plural = "사용자 가중치"

    def __str__(self) -> str:
        return f"{self.user} ({self.w_rent:.2f}/{self.w_amenity:.2f}/{self.w_transit:.2f})"
