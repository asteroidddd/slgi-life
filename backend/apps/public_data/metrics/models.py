"""
지표 (Metric) 모델 — Phase 1 RDS 통합용.

RDS(`dp_db`) 측 metric 35종 + 시계열 GuMetric 40,450행 / SeoulMetric 1,625행을
1:1로 매핑한다. PK는 RDS 비즈니스 키 그대로.
"""

from django.db import models


class Metric(models.Model):
    """지표 메타. RDS `metric` 35행.

    sub-plan 4.5A — schema.dbml 정합:
    - metric_code varchar(30→50)
    - name/unit/category NOT NULL (Char blank=False)
    - source_item varchar(200→100)
    - source_classification_code varchar(100→50)
    - source_agency/source_table/cycle/generation_method/remarks NULL 허용
    """

    metric_code = models.CharField(
        max_length=50, primary_key=True, help_text="지표 코드 (RDS metric.metric_code)"
    )
    name = models.CharField(max_length=100, help_text="지표 이름")
    unit = models.CharField(max_length=30, help_text="단위 (예: '명', '%', '원')")
    category = models.CharField(max_length=50, help_text="카테고리")
    cycle = models.CharField(
        max_length=20, null=True, blank=True, help_text="갱신 주기 (A/M/D)"
    )
    is_generated = models.BooleanField(
        default=False, help_text="생성 지표 여부 (raw가 아닌 파생)"
    )
    generation_method = models.TextField(null=True, blank=True, help_text="생성 방법 설명")
    source_agency = models.CharField(
        max_length=100, null=True, blank=True, help_text="출처 기관"
    )
    source_table = models.CharField(
        max_length=100, null=True, blank=True, help_text="출처 테이블/통계표"
    )
    source_item = models.CharField(
        max_length=100, null=True, blank=True, help_text="출처 항목명"
    )
    source_classification_code = models.CharField(
        max_length=50, null=True, blank=True, help_text="출처 분류 코드"
    )
    remarks = models.TextField(null=True, blank=True, help_text="비고")

    class Meta:
        db_table = "metric"
        verbose_name = "지표 메타"
        verbose_name_plural = "지표 메타"
        ordering = ["metric_code"]

    def __str__(self) -> str:
        return f"[{self.metric_code}] {self.name}"


class GuMetric(models.Model):
    """자치구별 지표 시계열. RDS `gu_metric` 40,450행. PK = (gu, date, metric)."""

    gu = models.ForeignKey(
        "regions.Gu",
        on_delete=models.CASCADE,
        related_name="metrics",
        db_column="gu_code",
    )
    date = models.DateField(help_text="기준일")
    metric = models.ForeignKey(
        Metric,
        on_delete=models.CASCADE,
        related_name="gu_values",
        db_column="metric_code",
    )
    value = models.DecimalField(
        max_digits=20, decimal_places=6, help_text="지표 값"
    )

    class Meta:
        db_table = "gu_metric"
        verbose_name = "자치구 지표"
        verbose_name_plural = "자치구 지표"
        unique_together = [("gu", "date", "metric")]
        indexes = [
            models.Index(fields=["gu", "metric", "-date"]),
            models.Index(fields=["metric", "-date"]),
            models.Index(fields=["date"]),
        ]
        ordering = ["-date", "gu_id", "metric_id"]

    def __str__(self) -> str:
        return f"{self.gu_id} {self.date} {self.metric_id}={self.value}"


class SeoulMetric(models.Model):
    """서울시 전체 지표 시계열. RDS `seoul_metric` 1,625행. PK = (seoul, date, metric)."""

    seoul = models.ForeignKey(
        "regions.Seoul",
        on_delete=models.CASCADE,
        related_name="metrics",
        db_column="seoul_code",
    )
    date = models.DateField(help_text="기준일")
    metric = models.ForeignKey(
        Metric,
        on_delete=models.CASCADE,
        related_name="seoul_values",
        db_column="metric_code",
    )
    value = models.DecimalField(
        max_digits=20, decimal_places=6, help_text="지표 값"
    )

    class Meta:
        db_table = "seoul_metric"
        verbose_name = "서울 지표"
        verbose_name_plural = "서울 지표"
        unique_together = [("seoul", "date", "metric")]
        indexes = [
            models.Index(fields=["metric", "-date"]),
            models.Index(fields=["date"]),
        ]
        ordering = ["-date", "metric_id"]

    def __str__(self) -> str:
        return f"{self.seoul_id} {self.date} {self.metric_id}={self.value}"
