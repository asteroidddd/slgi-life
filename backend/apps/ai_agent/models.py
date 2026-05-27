from django.conf import settings
from django.db import models


class UserAIAPIKey(models.Model):
    PROVIDER_OPENAI = "openai"
    PROVIDER_MINDLOGIC = "mindlogic"
    PROVIDER_CHOICES = (
        (PROVIDER_OPENAI, "OpenAI"),
        (PROVIDER_MINDLOGIC, "Mindlogic"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="ai_api_keys",
        on_delete=models.CASCADE,
    )
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    priority = models.PositiveSmallIntegerField(default=1)
    masked_key = models.CharField(max_length=255, blank=True, default="")
    encrypted_api_key = models.TextField()
    salt = models.CharField(max_length=128)
    nonce = models.CharField(max_length=128)
    tag = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_ai_api_key"
        unique_together = [("user", "provider")]
        ordering = ["priority", "provider"]
        indexes = [
            models.Index(fields=["user", "priority"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.provider}:{self.priority}"
