from __future__ import annotations

from django.db import models


class RentDealCache(models.Model):
    """Raw SQL managed cache table for front-end filtering payloads.

    The database table intentionally has no primary key or indexes. The id field
    is marked as the logical Django primary key only so the unmanaged model can
    be imported safely if needed.
    """

    id = models.CharField(max_length=20, primary_key=True)
    type_code = models.CharField(max_length=1)
    deposit = models.IntegerField(help_text="Deposit amount in KRW 10,000 units.")
    monthly_rent = models.SmallIntegerField(help_text="Monthly rent in KRW 10,000 units.")
    converted_rent = models.SmallIntegerField(
        help_text="Rounded monthly rent plus deposit conversion, in KRW 10,000 units."
    )
    area_m2 = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    contract_ymd = models.IntegerField(help_text="Contract date as YYYYMMDD.")

    class Meta:
        managed = False
        db_table = "rent_deal_cache"
        verbose_name = "rent deal cache"
        verbose_name_plural = "rent deal caches"

    @property
    def lng_lat(self) -> list[float] | None:
        if self.lng is None or self.lat is None:
            return None
        return [self.lng, self.lat]

    def __str__(self) -> str:
        return f"{self.id} [{self.type_code}] {self.deposit}/{self.monthly_rent}"
