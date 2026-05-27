// TanStack Query hook for the bbox-scoped transactions endpoint.
//
// Rendering policy (Phase 1b):
//   - Only enabled when `zoom >= MIN_ZOOM_FOR_PINS` (13). Below that we
//     do not render pins at all → skipping the network call entirely keeps
//     the user's panning lightweight and matches the empty-state hint UX.
//   - bbox precision is reduced to 4 decimal places (~11m) so micro pans
//     don't churn the cache key. Larger pans still re-fetch.
//
// Debouncing:
//   - The actual debouncing of map move events lives in the consumer
//     (TransactionPinLayer / MainMap) so that React state updates aren't
//     thrashed. This hook just consumes a stable Bbox.
import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import { getTransactionsBbox } from '@/lib/api';
import type {
  Bbox,
  TransactionFilters,
  TransactionsBboxResponse,
} from '@/types/api';

/** Below this zoom level we hide pins and skip API calls entirely. */
export const MIN_ZOOM_FOR_PINS = 13;

/** bbox grid quantization for cache key stability. ~11m at the equator. */
const BBOX_KEY_PRECISION = 4;

function quantize(n: number): number {
  const f = Math.pow(10, BBOX_KEY_PRECISION);
  return Math.round(n * f) / f;
}

interface UseTransactionsOptions {
  /** Current map bbox (SW + NE). Null while map is not yet ready. */
  bbox: Bbox | null;
  /** Current map zoom; query is disabled below MIN_ZOOM_FOR_PINS. */
  zoom: number;
  filters: TransactionFilters;
  /** Hard limit per request. Default 200 (matches backend default). */
  limit?: number;
}

export function useTransactions({
  bbox,
  zoom,
  filters,
  limit = 200,
}: UseTransactionsOptions): UseQueryResult<TransactionsBboxResponse> {
  const enabled = bbox != null && zoom >= MIN_ZOOM_FOR_PINS;

  // Quantize bbox so tiny mouse-drag jitter doesn't change the queryKey.
  const qBbox: Bbox | null = bbox
    ? {
        lng1: quantize(bbox.lng1),
        lat1: quantize(bbox.lat1),
        lng2: quantize(bbox.lng2),
        lat2: quantize(bbox.lat2),
      }
    : null;

  return useQuery({
    queryKey: [
      'transactions',
      'bbox',
      qBbox?.lng1,
      qBbox?.lat1,
      qBbox?.lng2,
      qBbox?.lat2,
      filters.deal_type,
      filters.from,
      filters.to,
      limit,
    ] as const,
    queryFn: () => getTransactionsBbox(qBbox as Bbox, filters, limit),
    enabled,
    // Backend has a 5-min cache; mirror that on the client so back-and-forth
    // panning over the same area doesn't re-hit the network.
    staleTime: 60_000,
    // Smooth UX while a new bbox is fetching: keep showing the last result.
    placeholderData: (previousData) => previousData,
  });
}
