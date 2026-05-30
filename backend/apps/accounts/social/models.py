from django.conf import settings
from django.db import models


class SocialAccount(models.Model):
    PROVIDER_KAKAO = "kakao"
    PROVIDER_CHOICES = (
        (PROVIDER_KAKAO, "Kakao"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="social_accounts",
        on_delete=models.CASCADE,
    )
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=191)
    email = models.EmailField(blank=True, default="")
    nickname = models.CharField(max_length=80, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_social_account"
        unique_together = ("provider", "provider_user_id")
        indexes = [
            models.Index(fields=["user", "provider"], name="user_social_user_id_58a646_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_user_id}"
