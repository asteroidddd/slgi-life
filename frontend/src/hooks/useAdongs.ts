// TanStack Query hooks for adong-related endpoints.
import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import { getCompare, getAdongDetail, getAdongGuMetrics, getAdongGuMetricsSeries, getAdongParks, getAdongPopulation, getAdongScores, getAdongSummary, getAdongTransitCongestion } from '@/lib/api';
import type {
  CompareResponse,
  AdongDetail,
  AdongGuMetricsResponse,
  AdongParksResponse,
  GuMetricSeriesResponse,
  AdongPopulationResponse,
  AdongScore,
  AdongSummary,
  TransitCongestionResponse,
  Weights,
} from '@/types/api';

/** Subscribe to /api/adongs/scores for a given weights triple.
 *  Refetches automatically when any weight value changes (queryKey).
 *  staleTime 60s mirrors the django-redis cache TTL on the backend.
 */
export function useAdongScores(weights: Weights): UseQueryResult<AdongScore[]> {
  return useQuery({
    queryKey: ['adongs', 'scores', weights.rent, weights.amenity, weights.transit] as const,
    queryFn: () => getAdongScores(weights),
    staleTime: 60_000,
  });
}

/** Subscribe to /api/adongs/:slug/summary for the slide-in adong panel.
 *  Disabled until a slug is selected (slug === null).
 *
 *  Re-fetches when slug or any weight changes. The backend recomputes the
 *  weighted score per request; the rule-based summary text depends only on
 *  raw scores so it stays stable across weight tweaks.
 */
export function useAdongSummary(
  slug: string | null,
  weights: Weights
): UseQueryResult<AdongSummary> {
  return useQuery({
    queryKey: [
      'adongs',
      'summary',
      slug,
      weights.rent,
      weights.amenity,
      weights.transit,
    ] as const,
    queryFn: () => getAdongSummary(slug as string, weights),
    enabled: slug != null,
    staleTime: 60_000,
  });
}

/** Subscribe to /api/compare for the compare page (SPEC 6.4).
 *  Backend preserves input slug order in the response. The hook is disabled
 *  when slugs is empty or `enabled` is false (e.g. before URL parsing).
 */
export function useCompare(
  slugs: string[],
  weights: Weights,
  enabled: boolean = true
): UseQueryResult<CompareResponse> {
  return useQuery({
    queryKey: [
      'compare',
      // Stable key: join here so reordering produces a different key.
      slugs.join(','),
      weights.rent,
      weights.amenity,
      weights.transit,
    ] as const,
    queryFn: () => getCompare(slugs, weights),
    enabled: enabled && slugs.length > 0,
    staleTime: 60_000,
  });
}

/** Subscribe to /api/adongs/:slug/detail for the detail page (SPEC 6.3).
 *  Disabled until a slug is available (route param undefined / empty).
 *  Refetches on weights changes — backend recomputes weighted score and
 *  vs_seoul_avg_pct each call.
 */
export function useAdongDetail(
  slug: string | null | undefined,
  weights: Weights
): UseQueryResult<AdongDetail> {
  return useQuery({
    queryKey: [
      'adongs',
      'detail',
      slug,
      weights.rent,
      weights.amenity,
      weights.transit,
    ] as const,
    queryFn: () => getAdongDetail(slug as string, weights),
    enabled: !!slug,
    staleTime: 60_000,
  });
}

/** Subscribe to /api/adongs/:slug/population — population time series.
 *  Disabled until slug is truthy. Backend caches 10min.
 */
export function useAdongPopulation(
  slug: string | null | undefined,
): UseQueryResult<AdongPopulationResponse> {
  return useQuery({
    queryKey: ['adongs', 'population', slug] as const,
    queryFn: () => getAdongPopulation(slug as string),
    enabled: !!slug,
    staleTime: 600_000, // 10 min — matches backend cache TTL
  });
}

/** Subscribe to /api/adongs/:slug/gu-metrics — gu-level metrics + Seoul avg.
 *  Disabled until slug is truthy. Backend caches 5min.
 */
export function useAdongGuMetrics(
  slug: string | null | undefined,
): UseQueryResult<AdongGuMetricsResponse> {
  return useQuery({
    queryKey: ['adongs', 'gu-metrics', slug] as const,
    queryFn: () => getAdongGuMetrics(slug as string),
    enabled: !!slug,
    staleTime: 300_000, // 5 min — matches backend cache TTL
  });
}

/** Subscribe to /api/adongs/:slug/gu-metrics/series — time-series for chart
 *  widgets (e.g. 교통사고/화재 추이). Disabled until slug + non-empty codes.
 *  Backend caches 5min per (gu, codes, years).
 */
export function useAdongGuMetricsSeries(
  slug: string | null | undefined,
  codes: string[],
  years?: number,
): UseQueryResult<GuMetricSeriesResponse> {
  // Sort codes so [A,B] and [B,A] share a cache entry — matches the backend
  // cache key (sorted_codes_joined) and de-dupes identical requests.
  const sortedCodes = [...codes].sort();
  return useQuery({
    queryKey: [
      'adongs',
      'gu-metrics-series',
      slug,
      sortedCodes.join(','),
      years ?? null,
    ] as const,
    queryFn: () => getAdongGuMetricsSeries(slug as string, codes, years),
    enabled: !!slug && codes.length > 0,
    staleTime: 300_000, // 5 min — matches backend cache TTL
  });
}

/** Subscribe to /api/adongs/:slug/transit-congestion — time-of-day congestion
 *  patterns (subway TOP3 + bus) + derived adong personality (SPEC 4.4 §C).
 *  Disabled until slug is truthy. Backend caches 5 min. */
export function useAdongTransitCongestion(
  slug: string | null | undefined,
): UseQueryResult<TransitCongestionResponse> {
  return useQuery({
    queryKey: ['adongs', 'transit-congestion', slug] as const,
    queryFn: () => getAdongTransitCongestion(slug as string),
    enabled: !!slug,
    staleTime: 300_000, // 5 min — matches backend cache TTL
  });
}


/** Subscribe to /api/adongs/:slug/parks — parks mapped to the adong.
 *  Disabled until slug is truthy. Parks rarely change so staleTime 10 min. */
export function useAdongParks(
  slug: string | null | undefined,
): UseQueryResult<AdongParksResponse> {
  return useQuery({
    queryKey: ['adongs', 'parks', slug] as const,
    queryFn: () => getAdongParks(slug as string),
    enabled: !!slug,
    staleTime: 600_000, // 10 min
  });
}
