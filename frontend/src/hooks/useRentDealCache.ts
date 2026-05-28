import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import { getRentDealCache } from '@/lib/api';
import type { RentDealCacheResponse } from '@/types/api';

const ONE_DAY_MS = 24 * 60 * 60 * 1000;

export function useRentDealCache(enabled: boolean): UseQueryResult<RentDealCacheResponse> {
  return useQuery({
    queryKey: ['rent-deals', 'cache'],
    queryFn: getRentDealCache,
    enabled,
    staleTime: ONE_DAY_MS,
    gcTime: ONE_DAY_MS,
  });
}
