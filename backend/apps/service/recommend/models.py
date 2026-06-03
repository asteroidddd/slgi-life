from django.db import models


class AdongUnivTime(models.Model):
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.CASCADE,
        db_column="adong_code",
        related_name="univ_times",
    )
    univ = models.ForeignKey(
        "univ.Univ",
        on_delete=models.CASCADE,
        db_column="univ_code",
        related_name="adong_times",
    )
    time = models.PositiveIntegerField(help_text="대학까지 예상 소요 시간(분)")

    class Meta:
        db_table = "adong_univ_time"
        verbose_name = "행정동-대학 시간"
        verbose_name_plural = "행정동-대학 시간"
        constraints = [
            models.UniqueConstraint(fields=["adong", "univ"], name="uq_adong_univ_time"),
        ]
        indexes = [
            models.Index(fields=["univ", "time"], name="adong_univ_time_univ_idx"),
            models.Index(fields=["adong"], name="adong_univ_time_adong_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.adong_id} {self.univ_id} {self.time}분"


class LdongUnivTime(models.Model):
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.CASCADE,
        db_column="ldong_code",
        related_name="univ_times",
    )
    univ = models.ForeignKey(
        "univ.Univ",
        on_delete=models.CASCADE,
        db_column="univ_code",
        related_name="ldong_times",
    )
    time = models.PositiveIntegerField(help_text="대학까지 예상 소요 시간(분)")

    class Meta:
        db_table = "ldong_univ_time"
        verbose_name = "법정동-대학 시간"
        verbose_name_plural = "법정동-대학 시간"
        constraints = [
            models.UniqueConstraint(fields=["ldong", "univ"], name="uq_ldong_univ_time"),
        ]
        indexes = [
            models.Index(fields=["univ", "time"], name="ldong_univ_time_univ_idx"),
            models.Index(fields=["ldong"], name="ldong_univ_time_ldong_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.ldong_id} {self.univ_id} {self.time}분"
