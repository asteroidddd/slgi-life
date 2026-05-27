// TanStack Query hooks for the preference-learning onboarding (SPEC 6.5, 11.4).
//
// Two hooks:
//   - usePreferencePairs(count, enabled) — GET /api/preference/pairs?count=N.
//     Gated by `enabled` so we only hit the network while the modal is open.
//   - useSubmitPreference() — POST /api/preference/submit, returns integer
//     weights {w_rent, w_amenity, w_transit} summing to 100.
//
// Source: docs/handoff/20260502-step7a-backend-preference.md
import { useMutation, useQuery } from '@tanstack/react-query';
import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query';

import { getPreferencePairs, submitPreferenceComparisons } from '@/lib/api';
import type {
  PreferencePairsResponse,
  PreferenceWeightsResponse,
  SubmitComparison,
} from '@/types/api';

/** Subscribe to /api/preference/pairs.
 *
 *  Only runs when `enabled` is true — typically wired to the modal's open
 *  state so we don't pre-fetch pairs before the user clicks "자동 추천".
 *  staleTime is short (30s) so each onboarding session asks the backend
 *  freshly; the dummy 5-adong dataset returns deterministic pairs anyway.
 */
export function usePreferencePairs(
  count: number = 5,
  enabled: boolean = true
): UseQueryResult<PreferencePairsResponse> {
  return useQuery({
    queryKey: ['preference', 'pairs', count] as const,
    queryFn: () => getPreferencePairs(count),
    enabled,
    staleTime: 30_000,
    // Pairs are deterministic per backend; refetching on focus/mount adds
    // no value and would reset the modal state mid-flow.
    refetchOnWindowFocus: false,
  });
}

/** POST /api/preference/submit. The mutation result is the estimated weight
 *  triple. Caller is responsible for applying it (e.g. setWeights).
 */
export function useSubmitPreference(): UseMutationResult<
  PreferenceWeightsResponse,
  Error,
  SubmitComparison[]
> {
  return useMutation({
    mutationFn: (comparisons: SubmitComparison[]) =>
      submitPreferenceComparisons(comparisons),
  });
}
