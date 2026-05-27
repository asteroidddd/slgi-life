// React Query hook for /api/adongs/match-counts (Phase 5).
//
// Studio Match 필터 변경 시 거래량 분포를 받아온다. slider drag 폭주를 막기
// 위해 200ms debounce — `filters` 가 빠르게 바뀌면 마지막 값만 fetch.
// (eng-review #11)
//
// placeholderData: prev — 필터 변경 중 잠깐 빈 화면 대신 이전 결과를 유지해
// 히트맵 깜빡임 최소화.

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import { getAdongMatchCounts } from '@/lib/api';
import type { MatchCountsResponse, MatchFilters } from '@/types/api';

const DEBOUNCE_MS = 200;

/** filters 가 빠르게 바뀌면 마지막 값만 살아남는 debounce 미러. */
function useDebouncedFilters(filters: MatchFilters, delay: number): MatchFilters {
  const [debounced, setDebounced] = useState(filters);
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(filters), delay);
    return () => window.clearTimeout(t);
  }, [filters, delay]);
  return debounced;
}

/** GET /api/adongs/match-counts 구독. 필터 변경은 200ms debounce. */
export function useAdongMatchCounts(
  filters: MatchFilters,
  enabled: boolean = true,
): UseQueryResult<MatchCountsResponse> {
  const debounced = useDebouncedFilters(filters, DEBOUNCE_MS);
  return useQuery({
    queryKey: [
      'adongs',
      'match-counts',
      debounced.deal_types.join(','),
      debounced.period,
      debounced.deposit_min,
      debounced.deposit_max,
      debounced.monthly_min,
      debounced.monthly_max,
      debounced.converted_min,
      debounced.converted_max,
      debounced.area_min,
      debounced.area_max,
    ] as const,
    queryFn: () => getAdongMatchCounts(debounced),
    enabled,
    staleTime: 30_000,
    placeholderData: (prev) => prev, // 필터 변경 시 이전 결과 유지 (깜빡임 ↓)
  });
}
