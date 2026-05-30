// Axios client + endpoint functions.
// All API calls go through this module. Hooks in src/hooks/* wrap these.
import axios from 'axios';
import type { AxiosInstance } from 'axios';

import type {
  Bbox,
  AdongScore,
  AIAPIKeyStatusResponse,
  AIContextPreferencePatch,
  AIContextPreferenceResponse,
  AIProvider,
  AgentQueryRequest,
  AgentQueryResponse,
  MatchCountsResponse,
  DashboardRegionIntro,
  AmenityBboxResponse,
  MedicalFacilitiesResponse,
  MapSearchResponse,
  MatchFilters,
  FavoriteItem,
  MePatchPayload,
  MeResponse,
  RentDealCacheResponse,
  RentDealLdongSummaryResponse,
  RentDealGuCodesResponse,
  RentDealGridSummaryResponse,
  RentListingAnalysisRequest,
  RentListingAnalysisResponse,
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

export async function getDashboardRegionIntro(
  regionType: 'adong' | 'ldong',
  slug: string,
): Promise<DashboardRegionIntro> {
  const path = regionType === 'ldong'
    ? `/dashboard/regions/ldongs/${slug}/intro`
    : `/dashboard/regions/adongs/${slug}/intro`;
  const { data } = await api.get<DashboardRegionIntro>(path);
  return data;
}

export async function getDashboardLdongAtPoint(
  lat: number,
  lng: number,
): Promise<DashboardRegionIntro> {
  const { data } = await api.get<DashboardRegionIntro>('/dashboard/regions/ldongs/lookup', {
    params: { lat, lng },
  });
  return data;
}

export async function getDashboardRegionAtPoint(
  regionType: 'adong' | 'ldong',
  lat: number,
  lng: number,
): Promise<DashboardRegionIntro> {
  const path = regionType === 'ldong'
    ? '/dashboard/regions/ldongs/lookup'
    : '/dashboard/regions/adongs/lookup';
  const { data } = await api.get<DashboardRegionIntro>(path, {
    params: { lat, lng },
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

export async function analyzeRentListing(
  payload: RentListingAnalysisRequest,
): Promise<RentListingAnalysisResponse> {
  const { data } = await api.post<RentListingAnalysisResponse>('/rent-deals/listing-analysis', payload, {
    timeout: 20_000,
  });
  return data;
}

function bboxToParam(bbox: Bbox): string {
  return `${bbox.lng1},${bbox.lat1},${bbox.lng2},${bbox.lat2}`;
}

export async function getRentDealLdongSummary(
  filters: MatchFilters,
): Promise<RentDealLdongSummaryResponse> {
  const { data } = await api.get<RentDealLdongSummaryResponse>('/rent-deals/summary/ldongs', {
    params: matchFiltersToParams(filters),
  });
  return data;
}

export async function getRentDealGridSummary(
  filters: MatchFilters,
  bbox: Bbox | null,
): Promise<RentDealGridSummaryResponse> {
  const params: Record<string, string | number> = matchFiltersToParams(filters);
  if (bbox) params.bbox = bboxToParam(bbox);
  const { data } = await api.get<RentDealGridSummaryResponse>('/rent-deals/summary/grids', {
    params,
  });
  return data;
}

export async function getRentDealGuCodes(bbox: Bbox): Promise<RentDealGuCodesResponse> {
  const { data } = await api.get<RentDealGuCodesResponse>('/rent-deals/cache/gus', {
    params: { bbox: bboxToParam(bbox) },
  });
  return data;
}

export async function getRentDealGuCacheText(guCode: string): Promise<string> {
  const { data } = await api.get<string>(`/rent-deals/cache/gus/${guCode}.tsv.gz`, {
    responseType: 'text',
    timeout: 600_000,
    transformResponse: [(value) => value],
  });
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
  conversationId?: string,
): Promise<AgentQueryResponse> {
  const body: AgentQueryRequest = { question };
  if (conversationId) body.conversation_id = conversationId;
  const { data } = await api.post<AgentQueryResponse>('/agent/query', body, {
    timeout: 180_000,
  });
  return data;
}

export async function getAgentDemoVisualization(): Promise<AgentQueryResponse> {
  const { data } = await api.get<AgentQueryResponse>('/agent/demo/visualization');
  return data;
}

// -------- Auth + Users -------------------------------------------------------
// Auth uses Django session cookies. Login starts through Kakao OAuth redirect.

export function getKakaoLoginUrl(): string {
  return `${baseURL.replace(/\/$/, '')}/auth/kakao/start`;
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

export async function deleteMe(confirmText: string): Promise<void> {
  await api.delete('/users/me', { data: { confirm_text: confirmText } });
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

export async function getAIContextPreference(): Promise<AIContextPreferenceResponse> {
  const { data } = await api.get<AIContextPreferenceResponse>('/agent/context-preferences');
  return data;
}

export async function updateAIContextPreference(
  payload: AIContextPreferencePatch,
): Promise<AIContextPreferenceResponse> {
  const { data } = await api.patch<AIContextPreferenceResponse>('/agent/context-preferences', payload);
  return data;
}


// Re-exports so callers can `import type { User } from '@/lib/api'` if they
// prefer barreling through the API module rather than `types/api`.
export type {
  FavoriteItem,
  MePatchPayload,
  MeResponse,
  SchoolOptionsResponse,
  User,
  AIAPIKeyStatusResponse,
  AIContextPreferencePatch,
  AIContextPreferenceResponse,
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


export async function getMedicalFacilities(params: {
  bbox: [number, number, number, number];
  categories?: string[];
  openNow?: boolean;
  limit?: number;
}): Promise<MedicalFacilitiesResponse> {
  const { data } = await api.get<MedicalFacilitiesResponse>('/medical/facilities', {
    params: {
      bbox: params.bbox.join(','),
      category: params.categories?.join(','),
      open_now: params.openNow ? 'true' : undefined,
      limit: params.limit,
    },
  });
  return data;
}
