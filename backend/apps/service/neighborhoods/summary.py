"""
한 줄 요약 generator (SPEC 11.3).

룰베이스. 점수 셋 (rent / amenity / transit, 각 0~100)을 받아 우선순위 순서로
첫 매칭되는 한국어 템플릿을 반환한다. LLM 호출은 비용 문제로 사용하지 않는다.

5/24 이후에 점수 카테고리 추가 시 룰 확장 가능.
"""

from __future__ import annotations


def generate_summary(score_rent: float, score_amenity: float, score_transit: float) -> str:
    """
    점수 3개를 받아 한 줄 요약 한국어 문자열 반환.

    파라미터:
        score_rent: 전월세 점수 (0~100, 높을수록 저렴)
        score_amenity: 생활시설 점수 (0~100, 높을수록 풍부)
        score_transit: 교통 점수 (0~100, 높을수록 좋음)

    반환: 한 줄 요약 문자열. 어떤 점수 조합이라도 매칭되도록 마지막에 기본값.

    룰 우선순위 (위에서 아래로 첫 매칭 반환):
        1. 셋 다 매우 좋음
        2. 매우 나쁜 조합
        3. 강한 조합 (역세권 + 저렴 등)
        4. 한쪽 강조
        5. 균형
        6. 기본값
    """

    rent = score_rent
    amenity = score_amenity
    transit = score_transit

    # ---- 1. 모든 지표 매우 좋음 ----
    if rent >= 70 and amenity >= 70 and transit >= 70:
        return "자취 입문자에게 추천 — 모든 면에서 균형이 좋아요"

    # ---- 2. 매우 나쁜 조합 (앞쪽에서 거른다) ----
    if rent < 30 and amenity < 50:
        return "비싸고 시설도 부족 — 자취 추천 어려워요"

    # ---- 3. 강한 조합 (역세권 + 저렴 / 가성비 등) ----
    if transit >= 80 and rent >= 70:
        return "역세권 + 저렴, 자취 1순위"

    if rent >= 80 and amenity >= 60:
        return "월세 저렴하고 시설도 무난, 가성비 좋아요"

    # ---- 4. 한쪽 강조 (대비가 큰 케이스) ----
    if transit >= 80 and amenity < 60:
        return "교통 좋고 생활시설 부족, 자취 입문자에게 추천"

    if amenity >= 80 and transit < 60:
        return "조용한 편이지만 생활시설 풍부"

    if rent < 30 and transit >= 70:
        return "월세는 비싸지만 교통 최고"

    if rent < 30 and amenity >= 70:
        return "월세는 비싸지만 시설은 풍부해요"

    # ---- 5. 두 지표 결합 (중간 강도) ----
    if rent >= 70 and amenity >= 70:
        return "월세 저렴하고 시설도 풍부, 가성비 좋아요"

    if amenity >= 70 and transit >= 70:
        return "시설·교통 모두 좋아 생활하기 편해요"

    if rent >= 70 and transit >= 70:
        return "월세 저렴하고 교통도 편해요"

    # ---- 6. 한쪽 강조 (덜 극단적인 케이스) ----
    if transit >= 80:
        return "교통이 강점인 동네"

    if amenity >= 80:
        return "생활시설이 풍부한 동네"

    if rent >= 80:
        return "월세 부담이 적은 동네"

    # ---- 7. 균형 (중간대 셋 다) ----
    if all(40 <= s <= 70 for s in (rent, amenity, transit)):
        return "균형 잡힌 동네예요"

    # ---- 8. 기본값 ----
    return "이 동네는 점수 기준상 평범한 편입니다"
