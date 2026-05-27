"""
Store + 카테고리 마스터 모델.

- BusinessCategory : 소상공인 카테고리 (sub-plan 4.5A 정합 완료, 본 sub-plan 영향 없음).
- KsciCategory     : 한국표준산업분류 (sub-plan 4.5A 정합 완료).
- Store            : 상가 raw. schema.dbml line 181~196 정합 (sub-plan 4.5B).

Store schema.dbml 정합 (sub-plan 4.5B):
- PK: varchar(64) → varchar(50). 'id varchar(50)'.
- name: blank=True → NOT NULL (schema.dbml line 183).
- branch_name: max_length 200 → 100 (schema.dbml line 184).
- category_code: nullable → NOT NULL FK (schema.dbml line 185).
- ksci_code: nullable 허용 (schema.dbml line 186, API 응답 결측 시 NULL).
- adong/ldong: nullable → NOT NULL FK (schema.dbml line 187~188).
- address: blank=True → NOT NULL, max_length 500 → 255 (schema.dbml line 189).
- location: nullable → NOT NULL (schema.dbml line 190).
- dong FK (neighborhoods.Dong) 제거 → adong FK (regions.Adong) 단일.

응답 dict key 보존 lock (lock 1) — Store는 frontend 직접 노출 없음 (Amenity로 통합).
"""

from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.db import models


class BusinessCategory(models.Model):
    """소상공인 카테고리. RDS `business_category` 247행.

    sub-plan 4.5A — schema.dbml 정합: 5개 컬럼 NOT NULL.
    """

    subcategory_code = models.CharField(
        max_length=20, primary_key=True, help_text="소분류 코드 (RDS PK)"
    )
    subcategory_name = models.CharField(max_length=100, help_text="소분류명")
    middle_category_code = models.CharField(max_length=20, help_text="중분류 코드")
    middle_category_name = models.CharField(max_length=100, help_text="중분류명")
    main_category_code = models.CharField(max_length=20, help_text="대분류 코드")
    main_category_name = models.CharField(max_length=100, help_text="대분류명")

    class Meta:
        db_table = "business_category"
        verbose_name = "소상공인 카테고리"
        verbose_name_plural = "소상공인 카테고리"
        ordering = ["subcategory_code"]
        indexes = [
            models.Index(fields=["middle_category_code"]),
            models.Index(fields=["main_category_code"]),
        ]

    def __str__(self) -> str:
        return f"[{self.subcategory_code}] {self.subcategory_name}"


class KsciCategory(models.Model):
    """한국표준산업분류. RDS `ksci_category` 1,196행.

    sub-plan 4.5A — schema.dbml 정합: 5개 컬럼 varchar(200→100) NOT NULL.
    """

    ksci_code = models.CharField(
        max_length=20, primary_key=True, help_text="KSCI 코드 (RDS PK)"
    )
    subcategory_name = models.CharField(max_length=100, help_text="소분류명")
    class_name = models.CharField(max_length=100, help_text="세분류명")
    subclass_name = models.CharField(max_length=100, help_text="세세분류명")
    middle_category_name = models.CharField(max_length=100, help_text="중분류명")
    main_category_name = models.CharField(max_length=100, help_text="대분류명")

    class Meta:
        db_table = "ksci_category"
        verbose_name = "한국표준산업분류"
        verbose_name_plural = "한국표준산업분류"
        ordering = ["ksci_code"]

    def __str__(self) -> str:
        return f"[{self.ksci_code}] {self.subcategory_name}"


class Store(models.Model):
    """상가 raw. RDS `store`. schema.dbml line 181~196 정합 (sub-plan 4.5B)."""

    # PK: schema.dbml 'id varchar(50)'.
    id = models.CharField(
        max_length=50, primary_key=True, help_text="상가 ID (RDS store.id, varchar(50))"
    )
    name = models.CharField(max_length=100, help_text="상호명 (NOT NULL)")
    branch_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="지점명 (schema.dbml NULL 허용)",
    )

    # 소상공인 카테고리 — schema.dbml NOT NULL.
    category = models.ForeignKey(
        BusinessCategory,
        on_delete=models.PROTECT,
        related_name="stores",
        db_column="category_code",
        help_text="소상공인 소분류 (schema.dbml NOT NULL).",
    )
    # KSCI — schema.dbml nullable 허용 (API 응답 결측 시 NULL).
    ksci = models.ForeignKey(
        KsciCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stores",
        db_column="ksci_code",
        help_text="한국표준산업분류 (API 응답 결측 시 NULL 허용).",
    )

    # 행정동/법정동. regions snapshot 교체 시 임시 NULL 허용 후 updater가 다시 채운다.
    adong = models.ForeignKey(
        "regions.Adong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stores",
        db_column="adong_code",
        help_text="행정동. regions snapshot 교체 시 NULL 허용.",
    )
    ldong = models.ForeignKey(
        "regions.Ldong",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stores",
        db_column="ldong_code",
        help_text="법정동. regions snapshot 교체 시 NULL 허용.",
    )

    address = models.CharField(max_length=255, help_text="주소 (NOT NULL)")
    location = gis_models.PointField(
        srid=4326, help_text="상가 위치 (WGS84, schema.dbml NOT NULL)."
    )

    class Meta:
        db_table = "store"
        verbose_name = "상가"
        verbose_name_plural = "상가"
        indexes = [
            models.Index(fields=["adong"]),
            models.Index(fields=["ldong"]),
            models.Index(fields=["category"]),
            models.Index(fields=["ksci"]),
            GistIndex(fields=["location"], name="store_location_gist_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.branch_name})" if self.branch_name else self.name
