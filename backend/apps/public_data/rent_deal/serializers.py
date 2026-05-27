"""RentDeal 시리얼라이저.

sub-plan 4.5B — model이 schema.dbml과 정합(housing_type 한글 raw, contract_date,
ldong FK)된 후에도 frontend 응답 dict key는 0 변경되도록 source 매핑으로 보존한다.

응답 dict key 보존 lock (lock 1):
- "id"               ← RentDeal.id (varchar(60))
- "date"             ← contract_date
- "deal_type"        ← housing_type을 영문 enum으로 매핑 (apt/officetel/villa/dagagu/danok)
- "area_m2"          ← area_m2
- "deposit"          ← deposit
- "monthly_rent"     ← monthly_rent
- "converted_rent"   ← derived (만원, 정수)
- "lat" / "lng"      ← location.y / location.x
- "jibun"            ← jibun
- "dong_name"        ← ldong.name (법정동명)
- "gu"               ← ldong.gu.name (구명)

이동 이력:
- sub-plan 2H: realestate → rent_deal 이동.
- sub-plan 4.5B: housing_type/contract_date/ldong 정합 + source 매핑 추가.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.public_data.rent_deal.models import HOUSING_TYPE_TO_DEAL_TYPE, RentDeal

from .utils import convert_to_monthly


class RentDealPinSerializer(serializers.ModelSerializer):
    """
    실거래 핀 한 건.

    응답 형식 (Phase 1 frontend가 그대로 소비, sub-plan 4.5B에서도 보존):
        {
            "id": "...",          # varchar(60) — sub-plan 4.5B PK 변경
            "date": "2026-04-15",
            "deal_type": "officetel",
            "area_m2": 23.4,
            "deposit": 5000,
            "monthly_rent": 50,
            "converted_rent": 75,
            "lat": 37.5663,
            "lng": 126.9783,
            "jibun": "필동 1-1",
            "dong_name": "필동",
            "gu": "중구",
        }
    """

    date = serializers.DateField(source="contract_date")
    deal_type = serializers.SerializerMethodField()
    # ldong은 NOT NULL FK이므로 source="ldong.name"로 항상 직접 매핑.
    dong_name = serializers.CharField(source="ldong.name", read_only=True)
    gu = serializers.CharField(source="ldong.gu.name", read_only=True)
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    converted_rent = serializers.SerializerMethodField()

    class Meta:
        model = RentDeal
        fields = (
            "id",
            "date",
            "deal_type",
            "area_m2",
            "deposit",
            "monthly_rent",
            "converted_rent",
            "lat",
            "lng",
            "jibun",
            "dong_name",
            "gu",
        )

    def get_deal_type(self, obj: RentDeal) -> str:
        """housing_type 한글 raw → 영문 enum (frontend 응답 key 보존용).

        예: '아파트' → 'apt', '연립다세대' → 'villa'. 매핑 실패 시 한글 그대로 반환.
        """
        return HOUSING_TYPE_TO_DEAL_TYPE.get(obj.housing_type, obj.housing_type)

    def get_lat(self, obj: RentDeal) -> float:
        # PointField: x=lng, y=lat. location__isnull=False로 view에서 필터링됨.
        return round(obj.location.y, 6)

    def get_lng(self, obj: RentDeal) -> float:
        return round(obj.location.x, 6)

    def get_converted_rent(self, obj: RentDeal) -> int:
        """환산월세 (만원, 정수). 보증금 환산 계수 0.005/월 (연 6%)."""
        return round(convert_to_monthly(obj.deposit, obj.monthly_rent))
