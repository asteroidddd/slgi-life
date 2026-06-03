// Amenity rank percentile helper (A-7a, design-polish-v2.md).
//
// R-3 amenity rows add a 4th cell `TOP {n}%`. The data does NOT live in
// /api/adongs/:slug/detail — the per-adong detail response has only `count` and
// `density_per_km2` per category, no peer distribution.
//
// To avoid expanding the backend (capstone scope), we compute the percentile
// on the client using `useAdongScores()` which is already cached for the map.
// `score_amenity` is one number per adong (the composite amenity axis) — we
// don't have per-category peer distributions, so every amenity row of a given
// adong shares the same percentile. The `category` arg is kept in the signature
// to match the plan's contract and to leave room for a future per-category
// expansion if the backend ever exposes it.
//
// Edge cases:
//   - Empty / undefined `allAdongs` → null (caller renders "—").
//   - All adongs share the same `score_amenity` (synthetic data) → null.
//     Plan A-7a mandates "—" not "TOP 0%" in this case.
//   - currentScore is non-finite → null.
//
// Output: integer 1..100 representing "TOP X%". Lower X is better
// (TOP 5% = better than 95% of adongs). Caller renders `TOP ${X}%`.

import type { AdongScore } from '@/features/common/types/api';

export function computeAmenityPercentile(
  allAdongs: AdongScore[] | undefined,
  // Reserved for future per-category distributions; currently unused —
  // see header comment.
  _category: string,
  currentScore: number,
): number | null {
  if (!allAdongs || allAdongs.length === 0) return null;
  if (!Number.isFinite(currentScore)) return null;

  const scores = allAdongs.map((d) => d.score_amenity).filter((s) => Number.isFinite(s));
  if (scores.length === 0) return null;

  // Synthetic-data edge case: every adong has the same score → no distribution.
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  if (min === max) return null;

  const lower = scores.filter((s) => s < currentScore).length;
  const percentile = (lower / scores.length) * 100;
  // Invert + round so "TOP X%" reads as "better than (100 - X)% of adongs".
  // Clamp to [1, 100] so we never render "TOP 0%".
  const top = Math.max(1, Math.min(100, Math.round(100 - percentile)));
  return top;
}
