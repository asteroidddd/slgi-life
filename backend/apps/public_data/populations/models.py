"""
법정동·행정동 인구 시계열 모델 (sub-plan 2C에서 regions에서 이동).

기존 `apps.public_data.regions.models`에 있던 LdongPopulation / AdongPopulation을
도메인 분리 차원에서 `apps.public_data.populations`로 옮긴 결과물이다.

DB 정책 (sub-plan 2C):
- 두 모델은 db_table을 RDS 테이블명과 동일하게 보존한다
  (`ldong_population` / `adong_population`).
- ForeignKey 대상은 문자열 참조(`"regions.Ldong"`, `"regions.Adong"`)를 유지하여
  app 간 순환 import를 방지한다.
- 본 sub-plan은 ORM 인식만 옮기는 SeparateDatabaseAndState 패턴을 쓴다 (DB 변경 0).
- AdongPopulation.adong FK는 sub-plan 2O에서 `regions.Adong` 마스터로 치환되었다.
  db_column은 `adong_code` 유지 → DB 변경 0.
"""

from django.db import models


class LdongPopulation(models.Model):
    """법정동 인구. RDS `ldong_population`. PK = (ldong, date).

    sub-plan 4.5A — schema.dbml 정합: 인구 4개 컬럼 NOT NULL.
    """

    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.CASCADE,
        related_name="populations",
        db_column="ldong_code",
    )
    date = models.DateField(help_text="기준일")
    total_population = models.IntegerField(help_text="총 인구")
    household_count = models.IntegerField(help_text="세대 수")
    male_population = models.IntegerField(help_text="남자 인구")
    female_population = models.IntegerField(help_text="여자 인구")

    class Meta:
        db_table = "ldong_population"
        verbose_name = "법정동 인구"
        verbose_name_plural = "법정동 인구"
        unique_together = [("ldong", "date")]
        indexes = [
            models.Index(fields=["ldong", "-date"]),
            models.Index(fields=["date"]),
        ]
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.ldong_id} {self.date} pop={self.total_population}"


class AdongPopulation(models.Model):
    """행정동 인구. RDS `adong_population`. PK = (adong, date).

    sub-plan 2O — Adong 마스터 FK로 치환 (이전: neighborhoods.Dong FK + to_field='code').
    db_column은 `adong_code` 유지 → DB 변경 0.
    """

    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.CASCADE,
        related_name="populations",
        db_column="adong_code",
    )
    date = models.DateField(help_text="기준일")
    total_population = models.IntegerField(help_text="총 인구")
    household_count = models.IntegerField(help_text="세대 수")
    male_population = models.IntegerField(help_text="남자 인구")
    female_population = models.IntegerField(help_text="여자 인구")

    class Meta:
        db_table = "adong_population"
        verbose_name = "행정동 인구"
        verbose_name_plural = "행정동 인구"
        unique_together = [("adong", "date")]
        indexes = [
            models.Index(fields=["adong", "-date"]),
            models.Index(fields=["date"]),
        ]
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.adong_id} {self.date} pop={self.total_population}"
