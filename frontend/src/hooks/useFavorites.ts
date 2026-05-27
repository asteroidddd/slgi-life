// TanStack Query hooks for the favorites + me endpoints (step 9).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import { addFavorite, getFavorites, removeFavorite } from '@/lib/api';
import type { FavoriteItem } from '@/types/api';

const FAVORITES_KEY = ['users', 'me', 'favorites'] as const;

/** GET /api/users/me/favorites — newest first. Disabled when not logged in.
 *  The backend already 401s for anon callers; we still gate via `enabled`
 *  so we don't fire a guaranteed-fail request from MyPage on logout.
 */
export function useFavorites(
  enabled: boolean = true
): UseQueryResult<FavoriteItem[]> {
  return useQuery({
    queryKey: FAVORITES_KEY,
    queryFn: getFavorites,
    enabled,
    staleTime: 60_000,
  });
}

/** POST /api/users/me/favorites — invalidates the favorites list on success. */
export function useAddFavorite() {
  const qc = useQueryClient();
  return useMutation<FavoriteItem, Error, string>({
    mutationFn: (slug: string) => addFavorite(slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: FAVORITES_KEY });
    },
  });
}

/** DELETE /api/users/me/favorites/:slug — invalidates on success. */
export function useRemoveFavorite() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (slug: string) => removeFavorite(slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: FAVORITES_KEY });
    },
  });
}
