// Axios client + endpoint functions.
// All API calls go through this module. Hooks in src/hooks/* wrap these.
import axios from 'axios';
import type { AxiosInstance } from 'axios';

import type {
  Bbox,
  AdongScore,
  AIAPIKeyStatusResponse,
  AIProvider,
  AgentQueryRequest,
  AgentQueryResponse,
  MatchCountsResponse,
  AmenityBboxResponse,
  MapSearchResponse,
  MatchFilters,
  FavoriteItem,
  LoginPayload,
  MePatchPayload,
  MeResponse,
  RegisterPayload,
  RentDealCacheResponse,
  RentConversionRateResponse,
  RentDealPin,
  SchoolOptionsResponse,
  TransactionFilters,
  TransactionsBboxResponse,
  User,
  Weights,
} from '@/types/api';

const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export const api: AxiosInstance = axios.create({
  baseURL,
  timeout: 10_000,
  // Required for Django session cookies. The backend marks all auth routes
  // CSRF-exempt (see step9a handoff) so no token wrangling is needed.
  withCredentials: true,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
});


export async function getMapSearch(q: string): Promise<MapSearchResponse> {
  const { data } = await api.get<MapSearchResponse>('/search', { params: { q } });
  return data;
}

export async function getAdongScores(weights: Weights): Promise<AdongScore[]> {
  const { data } = await api.get<AdongScore[]>('/heatmap/adongs/scores', {
    params: {
      w_rent: weights.rent,
      w_amenity: weights.amenity,
      w_transit: weights.transit,
    },
  });
  return data;
}

export async function getLdongScores(weights: Weights): Promise<AdongScore[]> {
  const { data } = await api.get<AdongScore[]>('/heatmap/ldongs/scores', {
    params: {
      w_rent: weights.rent,
      w_amenity: weights.amenity,
      w_transit: weights.transit,
    },
  });
  return data;
}


export async function getAdongMatchCounts(
  filters: MatchFilters,
): Promise<MatchCountsResponse> {
  const { data } = await api.get<MatchCountsResponse>('/rent-deals/match-counts', {
    params: matchFiltersToParams(filters),
  });
  return data;
}

export async function getRentConversionRate(): Promise<RentConversionRateResponse> {
  const { data } = await api.get<RentConversionRateResponse>('/rent-deals/conversion-rate');
  return data;
}

export async function getRentDealCache(): Promise<RentDealCacheResponse> {
  const { data } = await api.get<RentDealCacheResponse>('/rent-deals/cache', {
    timeout: 600_000,
  });
  return data;
}

export async function getRentDealDetail(id: string): Promise<RentDealPin> {
  const { data } = await api.get<RentDealPin>(`/rent-deals/${id}`);
  return data;
}


function matchFiltersToParams(filters: MatchFilters): Record<string, string | number> {
  return {
    deal_types: filters.deal_types.join(','),
    period: filters.period,
    filter_mode: filters.filter_mode,
    deposit_min: filters.deposit_min,
    deposit_max: filters.deposit_max,
    monthly_min: filters.monthly_min,
    monthly_max: filters.monthly_max,
    converted_min: filters.converted_min,
    converted_max: filters.converted_max,
    area_min: filters.area_min,
    area_max: filters.area_max,
  };
}

export async function getTransactionsBbox(
  bbox: Bbox,
  filters: TransactionFilters,
  limit: number = 200
): Promise<TransactionsBboxResponse> {
  const params: Record<string, string | number> = {
    bbox: `${bbox.lng1},${bbox.lat1},${bbox.lng2},${bbox.lat2}`,
    limit,
  };
  // 'all' is a valid filter token on the backend (no filter applied), but we
  // still send it explicitly so the URL is deterministic for caching.
  params.deal_type = filters.deal_type;
  if (filters.from) params.from = filters.from;
  if (filters.to) params.to = filters.to;

  const { data } = await api.get<TransactionsBboxResponse>(
    '/transactions/bbox',
    { params }
  );
  return data;
}

export async function postAgentQuery(
  question: string,
): Promise<AgentQueryResponse> {
  const body: AgentQueryRequest = { question };
  const { data } = await api.post<AgentQueryResponse>('/agent/query', body, {
    timeout: 180_000,
  });
  return data;
}

// -------- Auth + Users (SPEC 6.6, 9 — step 9) ------------------------------
// All routes rely on the session cookie set by Django. Make sure axios
// `withCredentials` stays true (set above on the shared instance).

/** POST /api/auth/register — creates the user and auto-logs in. */
export async function register(payload: RegisterPayload): Promise<MeResponse> {
  const { data } = await api.post<MeResponse>('/auth/register', payload);
  return data;
}

/** POST /api/auth/login — sets the session cookie. */
export async function login(payload: LoginPayload): Promise<MeResponse> {
  const { data } = await api.post<MeResponse>('/auth/login', payload);
  return data;
}

/** POST /api/auth/logout — idempotent (200 even if not logged in). */
export async function logout(): Promise<void> {
  await api.post('/auth/logout');
}

/** GET /api/users/me — used on app boot to restore session. */
export async function getMe(): Promise<MeResponse> {
  const { data } = await api.get<MeResponse>('/users/me');
  return data;
}


/** PATCH /api/users/me — partial profile update. */
export async function patchMe(payload: MePatchPayload): Promise<MeResponse> {
  const { data } = await api.patch<MeResponse>('/users/me', payload);
  return data;
}

export async function getUniversityOptions(): Promise<SchoolOptionsResponse> {
  const { data } = await api.get<SchoolOptionsResponse>('/users/universities');
  return data;
}

export async function getFavorites(): Promise<FavoriteItem[]> {
  const { data } = await api.get<FavoriteItem[]>('/users/me/favorites');
  return data;
}

/** POST /api/users/me/favorites — adds a adong by slug. */
export async function addFavorite(slug: string): Promise<FavoriteItem> {
  const { data } = await api.post<FavoriteItem>('/users/me/favorites', {
    slug,
  });
  return data;
}

/** DELETE /api/users/me/favorites/:slug — 204 on success. */
export async function removeFavorite(slug: string): Promise<void> {
  await api.delete(`/users/me/favorites/${slug}`);
}

export async function getAIAPIKeys(): Promise<AIAPIKeyStatusResponse> {
  const { data } = await api.get<AIAPIKeyStatusResponse>('/agent/api-keys');
  return data;
}

export async function saveAIAPIKey(payload: {
  provider: AIProvider;
  api_key: string;
  passphrase: string;
  priority: number;
}): Promise<AIAPIKeyStatusResponse> {
  const { data } = await api.post<AIAPIKeyStatusResponse>('/agent/api-keys', payload);
  return data;
}

export async function unlockAIAPIKeys(passphrase: string): Promise<AIAPIKeyStatusResponse> {
  const { data } = await api.post<AIAPIKeyStatusResponse>('/agent/api-keys/unlock', { passphrase });
  return data;
}

export async function deleteAIAPIKey(provider: AIProvider): Promise<void> {
  await api.delete(`/agent/api-keys/${provider}`);
}


// Re-exports so callers can `import type { User } from '@/lib/api'` if they
// prefer barreling through the API module rather than `types/api`.
export type {
  FavoriteItem,
  LoginPayload,
  MePatchPayload,
  MeResponse,
  RegisterPayload,
  SchoolOptionsResponse,
  User,
  AIAPIKeyStatusResponse,
  AIProvider,
};


export async function getAmenitiesBbox(params: {
  bbox: [number, number, number, number];
  categories?: string[];
  limit?: number;
}): Promise<AmenityBboxResponse> {
  const { data } = await api.get<AmenityBboxResponse>('/amenities/bbox', {
    params: {
      bbox: params.bbox.join(','),
      categories: params.categories?.join(','),
      limit: params.limit,
    },
  });
  return data;
}
