"""
선호 학습 가중치 추정 (SPEC 11.4).

5번 비교 결과(승자/패자 동의 raw 점수 3종)로부터 사용자 가중치
(w_rent, w_amenity, w_transit)를 단순 Logistic Regression으로 추정.

핵심 모델:
    P(won > lost | w) = sigmoid( w · (won_feat - lost_feat) )
    -log L(w) = sum log(1 + exp( -w · diff ))

scipy.optimize.minimize SLSQP로 합=1, 0~1 제약 하에서 최소화.

이 모듈은 무상태(Stateless) — 입력 list만으로 결과 dict 반환.
9단계에서 UserPreference 모델이 추가되면 결과를 그곳에 저장.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import minimize


# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

# 균등 초기값 / 0건 fallback. 합 1이 정확히 되도록 마지막 컴포넌트로 잔차 흡수.
EQUAL_WEIGHTS: dict[str, float] = {"rent": 0.33, "amenity": 0.33, "transit": 0.34}

# 0.5% 미만 컴포넌트는 0으로 라운딩 (응답 시 정수 % 변환 시 깔끔하게).
ZERO_THRESHOLD = 0.005

# 응답 정수 % 변환 후 합 100 보장을 위해, 모든 양수 컴포넌트에 최소 0.01 보장.
MIN_POSITIVE = 0.01


# ---------------------------------------------------------------------------
# 내부 유틸
# ---------------------------------------------------------------------------


def _neg_log_likelihood(
    w: np.ndarray, diffs: np.ndarray
) -> float:
    """
    NLL = sum log(1 + exp(-w · diff_i))

    수치 안정 버전: log(1+exp(-x)) = softplus(-x) = max(-x, 0) + log(1+exp(-|x|))
    np.logaddexp(0, -x)가 정확히 그 표현 — overflow 안전.
    """
    z = diffs @ w  # shape (N,)
    return float(np.sum(np.logaddexp(0.0, -z)))


def _round_and_normalize(w: np.ndarray) -> dict[str, float]:
    """
    최적화 결과 w(합 1, 비음수)를 응답용 dict로 변환.

    1) 0.5% 미만은 0으로 라운딩
    2) 합이 1이 되도록 가장 큰 컴포넌트가 잔차 흡수
    3) 응답 시 정수 % 변환을 고려해 모든 양수에 최소 0.01 보장
    """
    keys = ("rent", "amenity", "transit")
    arr = np.asarray(w, dtype=float)

    # 음수 방지 (수치 오차로 -1e-12 같은 값 가능)
    arr = np.clip(arr, 0.0, 1.0)

    # 1) 임계값 미만 → 0
    arr[arr < ZERO_THRESHOLD] = 0.0

    # 2) 정규화: 합이 0이면 균등으로
    s = arr.sum()
    if s <= 0:
        return dict(EQUAL_WEIGHTS)
    arr = arr / s

    # 3) 가장 큰 컴포넌트에 잔차 흡수해 합 == 1 보장 (부동소수 누적 오차 처리)
    largest = int(np.argmax(arr))
    arr[largest] += 1.0 - arr.sum()

    return {k: float(v) for k, v in zip(keys, arr)}


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------


def estimate_weights(
    comparisons: list[
        tuple[tuple[float, float, float], tuple[float, float, float]]
    ],
) -> dict[str, float]:
    """
    Bradley-Terry / Logistic Regression으로 사용자 가중치 추정.

    파라미터:
        comparisons: [(won_features, lost_features), ...]
          - 각 features = (rent, amenity, transit) raw 점수 (0~100).
          - won = 사용자가 더 끌린다고 고른 동의 점수.
          - lost = 다른 쪽 동의 점수.

    반환:
        {"rent": w_rent, "amenity": w_amenity, "transit": w_transit}
        - 모두 0 이상, 합 = 1
        - 0.5% 미만 컴포넌트는 0으로 라운딩 (잔차는 최대 컴포넌트가 흡수)
        - comparisons가 비어있으면 균등 (0.33/0.33/0.34) 반환

    SPEC 11.4 50줄 단순 버전. PyMC 같은 베이지안 X.
    """
    if not comparisons:
        return dict(EQUAL_WEIGHTS)

    # 차이 벡터 행렬 (N, 3)
    diffs = np.array(
        [
            [w_f[0] - l_f[0], w_f[1] - l_f[1], w_f[2] - l_f[2]]
            for w_f, l_f in comparisons
        ],
        dtype=float,
    )

    # 모든 비교가 동일한 점수 쌍이면 (예: 같은 동을 won/lost로) NLL이 상수.
    # 이 경우 균등 반환.
    if not np.any(diffs):
        return dict(EQUAL_WEIGHTS)

    # 초기값 [1/3, 1/3, 1/3]
    w0 = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0])

    # 합 = 1 등식 제약 + 각 0~1 박스 제약 → SLSQP
    constraints = ({"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)},)
    bounds = [(0.0, 1.0)] * 3

    result = minimize(
        _neg_log_likelihood,
        w0,
        args=(diffs,),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-9, "maxiter": 200},
    )

    if not result.success or not np.all(np.isfinite(result.x)):
        # 최적화 실패 시 균등 fallback (입력 quirky 케이스 방어)
        return dict(EQUAL_WEIGHTS)

    return _round_and_normalize(result.x)


def to_integer_percent(weights: dict[str, float]) -> dict[str, int]:
    """
    optimizer가 낸 float 가중치(합=1)를 정수 % 3개(합=100)로 변환.

    SPEC 11.4 응답 spec: w_rent / w_amenity / w_transit 각각 0~100 정수, 합 = 100.

    반올림 누적으로 합이 99 또는 101이 될 수 있으므로,
    largest-remainder 방식으로 보정 — 가장 큰 잔차를 가진 컴포넌트가
    1을 가져가거나 잃는다.
    """
    keys = ("rent", "amenity", "transit")
    raw = np.array([weights[k] * 100.0 for k in keys], dtype=float)

    # floor + 큰 잔차 우선 1 분배
    floors = np.floor(raw).astype(int)
    remainders = raw - floors
    deficit = 100 - int(np.sum(floors))

    if deficit > 0:
        # 잔차가 큰 인덱스부터 +1
        order = np.argsort(-remainders)  # 내림차순
        for i in range(deficit):
            floors[order[i % 3]] += 1
    elif deficit < 0:
        # 잔차가 작은 인덱스부터 -1 (0 이하로 떨어지지 않게 안전 처리)
        order = np.argsort(remainders)  # 오름차순
        i = 0
        while deficit < 0 and i < 100:
            idx = order[i % 3]
            if floors[idx] > 0:
                floors[idx] -= 1
                deficit += 1
            i += 1

    # 0~100 범위 보정 (수치적 안전)
    floors = np.clip(floors, 0, 100)
    # 마지막으로 합 == 100 강제 (부동소수/극단 케이스)
    diff = 100 - int(np.sum(floors))
    if diff != 0:
        # 가장 큰 컴포넌트에 잔차 흡수
        largest = int(np.argmax(floors))
        floors[largest] += diff

    return {k: int(v) for k, v in zip(keys, floors)}
