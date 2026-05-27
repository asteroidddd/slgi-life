// Rent conversion helper — boundary-shared with the backend.
//
// Why this exists:
//   서울 자취 시장은 보증금-월세 trade-off 가 큼. 같은 임차 부담이라도
//   전세 2억(월세 0) vs 월세 1천(월세 80) 식으로 표기되어, raw 월세만
//   비교하면 보증금 큰 동이 부당하게 "싸 보임" — 졸업 발표에서 받기
//   쉬운 질문을 차단하기 위해 환산값을 UI 전반에 노출한다.
//
// Single source of truth:
//   백엔드 `apps.public_data.realestate.utils.convert_to_monthly` 와 동일 계수.
//   변경 시 백엔드/프런트 동시 수정 필요. SPEC §11.2 와 정합.
//   (서울 평균 전환률 ≈ 6%/년 = 0.005/월)

/** 보증금→월세 환산 계수 (1만원의 보증금이 한 달에 만들어내는 환산 월세).
 *  연 6% 전환률 가정. 백엔드와 절대 일치해야 함. */
export const MONTHLY_CONVERSION_RATE = 0.005;

/** 환산월세(만원) = 월세 + 보증금 × 계수.
 *  단위는 모두 만원. 정수가 아닌 부동소수점 결과를 반환하므로 표시 시
 *  반올림은 호출자 책임. */
export function convertToMonthly(deposit: number, monthlyRent: number): number {
  return monthlyRent + deposit * MONTHLY_CONVERSION_RATE;
}

/** 표시용 환산월세 라벨 — 정수 만원으로 반올림 + "만원" 단위 부착.
 *  예: deposit=1000, monthlyRent=80 → "85만원" (= 80 + 5).
 *  예: deposit=20000, monthlyRent=0  → "100만원" (전세 케이스). */
export function formatConvertedRent(deposit: number, monthlyRent: number): string {
  return `${Math.round(convertToMonthly(deposit, monthlyRent))}만원`;
}
