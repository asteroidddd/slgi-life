from django.conf import settings
from django.db import models


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="favorites",
        on_delete=models.CASCADE,
    )
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
            models.Index(fields=["user", "-created_at"], name="user_favori_user_id_9351bd_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} ♡ {self.adong}"
