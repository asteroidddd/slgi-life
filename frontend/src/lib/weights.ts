// Helpers for the three weight sliders on the main map (SPEC 6.1).
// Constraint: rent + amenity + transit must equal 100. Each is an integer 0~100.
//
// When a user drags one slider, the other two should redistribute proportionally
// so the trio always sums to 100. This keeps the UI honest with the backend
// validation (`abs(sum - 100) > 1` returns 400).
import type { Weights } from '@/types/api';

export type WeightKey = keyof Weights;

/** Adjust one weight key to `nextValue` and proportionally redistribute the
 *  remainder across the other two keys, preserving their existing ratio.
 *
 *  Edge cases:
 *  - If the other two are both zero, split the remainder evenly between them.
 *  - All output values are integers 0~100; sum is exactly 100 (rounding error
 *    absorbed into the larger of the two siblings).
 */
export function rebalanceWeights(
  current: Weights,
  changedKey: WeightKey,
  nextValue: number
): Weights {
  const v = clampInt(nextValue, 0, 100);
  const otherKeys = (['rent', 'amenity', 'transit'] as WeightKey[]).filter(
    (k) => k !== changedKey
  ) as [WeightKey, WeightKey];

  const remainder = 100 - v;
  const [aKey, bKey] = otherKeys;
  const aPrev = current[aKey];
  const bPrev = current[bKey];
  const sumPrev = aPrev + bPrev;

  let aNext: number;
  let bNext: number;
  if (sumPrev === 0) {
    aNext = Math.floor(remainder / 2);
    bNext = remainder - aNext;
  } else {
    aNext = Math.round((aPrev / sumPrev) * remainder);
    bNext = remainder - aNext; // ensures exact sum
    // Clamp safety
    if (aNext < 0) aNext = 0;
    if (bNext < 0) bNext = 0;
    if (aNext > 100) aNext = 100;
    if (bNext > 100) bNext = 100;
    // Re-derive the partner if the clamp shifted things
    if (aNext + bNext !== remainder) {
      bNext = remainder - aNext;
    }
  }

  const next: Weights = { ...current, [changedKey]: v };
  next[aKey] = aNext;
  next[bKey] = bNext;
  return next;
}

function clampInt(v: number, min: number, max: number): number {
  if (Number.isNaN(v)) return min;
  return Math.max(min, Math.min(max, Math.round(v)));
}
