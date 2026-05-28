import { useQuery } from '@tanstack/react-query';

import { getAdongScores, getLdongScores } from '@/lib/api';
import type { Weights } from '@/types/api';

export function useAdongScores(weights: Weights) {
  return useQuery({
    queryKey: ['adongs', 'scores', weights] as const,
    queryFn: () => getAdongScores(weights),
    staleTime: 300_000,
  });
}

export function useLdongScores(weights: Weights) {
  return useQuery({
    queryKey: ['ldongs', 'scores', weights] as const,
    queryFn: () => getLdongScores(weights),
    staleTime: 300_000,
  });
}
