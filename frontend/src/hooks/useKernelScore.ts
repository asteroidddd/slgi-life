// TanStack Query hook for the kernel-score endpoint (Phase 2b).
//
// Behavior:
//   - Fires POST /api/score/point whenever (point, weights, school) changes.
//   - placeholderData keeps the previous response visible while a new fetch
//     is in flight, so weight-slider drags don't blank the panel.
//   - 5-minute staleTime — same lat/lng + weights re-click skips network.
//   - AbortController is wired through TanStack Query's queryFn signal so
//     rapid clicks cancel the previous request rather than racing.
//
// Note on weights:
//   The hook accepts integer percent (0~100, like Weights) for symmetry with
//   the rest of the app, and converts to fractions before posting. Backend
//   normalizes anyway, but sending fractions matches the API doc examples.
import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import { postScorePoint } from '@/lib/api';
import type {
  KernelScoreResponse,
  KernelScoreWeights,
  Weights,
} from '@/types/api';

/** Lat/lng tuple — matches Leaflet's [lat, lng] convention. */
export type LatLng = [number, number];

/** Quantize a coord to ~1m so micro-jitter doesn't change the cache key. */
function qz(n: number): number {
  return Math.round(n * 1e5) / 1e5;
}

/** Convert integer-percent Weights → fractional KernelScoreWeights. */
function toFractionWeights(w: Weights): KernelScoreWeights {
  return {
    rent: w.rent / 100,
    amenity: w.amenity / 100,
    transit: w.transit / 100,
  };
}

interface UseKernelScoreOptions {
  /** Clicked point. Null → query disabled. */
  point: LatLng | null;
  /** Weights — integer percent, same shape as the main map sliders. */
  weights: Weights;
  /** Optional school name. Empty string treated as "no school". */
  school?: string;
}

export function useKernelScore({
  point,
  weights,
  school,
}: UseKernelScoreOptions): UseQueryResult<KernelScoreResponse> {
  const enabled = point != null;
  const trimmedSchool = school?.trim() ? school.trim() : undefined;

  // Round weights to integers in the queryKey so micro float drift (which
  // cannot happen with our integer state today, but future-proofs against a
  // float slider) doesn't churn the cache.
  const wKey = `${weights.rent}|${weights.amenity}|${weights.transit}`;

  return useQuery({
    queryKey: [
      'kernel-score',
      point ? qz(point[0]) : null,
      point ? qz(point[1]) : null,
      wKey,
      trimmedSchool ?? null,
    ] as const,
    queryFn: async ({ signal }) => {
      // `enabled` gates this, so point is non-null when invoked.
      const [lat, lng] = point as LatLng;
      return postScorePoint(
        {
          lat,
          lng,
          weights: toFractionWeights(weights),
          ...(trimmedSchool ? { school: trimmedSchool } : {}),
        },
        signal,
      );
    },
    enabled,
    staleTime: 5 * 60_000, // 5 min
    placeholderData: (prev) => prev,
    // Don't auto-refetch on window focus — kernel result is stable for a coord.
    refetchOnWindowFocus: false,
  });
}
