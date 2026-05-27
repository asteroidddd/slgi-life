"""전월세 환산 유틸 — SPEC §11.2 가정과 일관 (계수 0.005/월 ≈ 연 6% 전환률).

서울 자취 시장은 보증금-월세 trade-off로 가격이 표현된다.
같은 가격대의 매물도 전세/반전세/월세 형태로 호가가 다양해, raw 월세만 비교하면
보증금이 큰 동(낮은 raw 월세)이 부당하게 "싸 보이는" 왜곡이 생긴다.

본 모듈은 이 왜곡을 해소할 표준 환산식을 단일 진실로 제공한다.

표준 전월세 환산식:
    환산월세(만원) = 월세(만원) + 보증금(만원) × 0.005

계수 0.005 = 연 6% 전월세전환률 / 12개월. 국토부 공시 기준 서울 평균
(4~6%)에 정렬한 값. service scoring updater 의 score_rent 계산과 동일 가정을
공유하므로, 본 유틸을 임포트하여 사용한다.

이동 이력:
- sub-plan 2H: `apps.public_data.realestate.utils` → `apps.public_data.rent_deal.utils`로 이동.
"""

from __future__ import annotations


# 보증금 → 월세 환산 계수 (per month).
# 연 6% 전환률 / 12개월 = 0.005. 변경 시 score_rent 재계산 필요.
MONTHLY_CONVERSION_RATE: float = 0.005


def convert_to_monthly(deposit: float, monthly_rent: float) -> float:
    """환산월세(만원) = 월세 + 보증금 × 계수.

    파라미터
    --------
    deposit       : 보증금 (만원). 음수는 0으로 클램프.
    monthly_rent  : 월세 (만원). 0 이면 전세로 해석되어 보증금만 환산됨.

    반환
    ----
    float — 환산 월세 (만원). 입력이 0 이상이면 결과도 0 이상.

    동작
    ----
    - 전세 (monthly_rent=0)  → deposit × 0.005
    - 반전세                 → monthly_rent + deposit × 0.005
    - 월세 (deposit ~ 0)     → ~ monthly_rent
    """
    d = max(0.0, float(deposit))
    m = max(0.0, float(monthly_rent))
    return m + d * MONTHLY_CONVERSION_RATE
