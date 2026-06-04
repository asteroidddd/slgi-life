// Axios client + endpoint functions.
// All API calls go through this module. Hooks in src/hooks/* wrap these.
import axios from 'axios';
import type { AxiosInstance } from 'axios';

import type {
  AdongScore,
  AIAPIKeyStatusResponse,
  AIContextPreferencePatch,
  AIContextPreferenceResponse,
  AIProvider,
  AgentQueryRequest,
  AgentQueryResponse,
  DashboardRegionIntro,
  AmenityBboxResponse,
  MedicalFacilitiesResponse,
  MedicalSpecialtyGroupsResponse,
  MapSearchResponse,
  NeighborhoodCommuteTimeResponse,
  NeighborhoodCompareResponse,
  FavoriteItem,
  MePatchPayload,
  MeResponse,
  RentListingAnalysisRequest,
  RentListingAnalysisResponse,
  RentConversionRateResponse,
  RecommendationRegionsResponse,
  SchoolOptionsResponse,
  SavedCandidateRegion,
  SavedRecommendationConditions,
  UserCandidateRegionsResponse,
  UserRecommendationConditionsResponse,
  User,
  Weights,
} from '@/features/common/types/api';

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

export async function getUserCandidateRegions(): Promise<UserCandidateRegionsResponse> {
  const { data } = await api.get<UserCandidateRegionsResponse>('/users/me/candidate-regions');
  return data;
}

export async function saveUserCandidateRegions(items: SavedCandidateRegion[]): Promise<UserCandidateRegionsResponse> {
  const { data } = await api.put<UserCandidateRegionsResponse>('/users/me/candidate-regions', { items });
  return data;
}

export async function getNeighborhoodComparison(
  items: Array<Pick<SavedCandidateRegion, 'regionLevel' | 'slug'>>,
  universityId?: string,
): Promise<NeighborhoodCompareResponse> {
  const regions = items
    .slice(0, 10)
    .map((item) => `${item.regionLevel}:${item.slug}`)
    .join(',');
  const { data } = await api.get<NeighborhoodCompareResponse>('/compare/neighborhoods', {
    params: { regions, university_id: universityId || undefined },
    timeout: 20_000,
  });
  return data;
}

export async function getNeighborhoodCommuteTime(
  regionType: SavedCandidateRegion['regionLevel'],
  slug: string,
  universityId: string,
): Promise<NeighborhoodCommuteTimeResponse> {
  const { data } = await api.get<NeighborhoodCommuteTimeResponse>('/compare/commute-time', {
    params: {
      region_type: regionType,
      slug,
      university_id: universityId,
    },
    timeout: 20_000,
  });
  return data;
}

export async function getUserRecommendationConditions(): Promise<UserRecommendationConditionsResponse> {
  const { data } = await api.get<UserRecommendationConditionsResponse>('/users/me/recommendation-conditions');
  return data;
}

export async function saveUserRecommendationConditions(
  conditions: SavedRecommendationConditions,
): Promise<UserRecommendationConditionsResponse> {
  const { data } = await api.put<UserRecommendationConditionsResponse>('/users/me/recommendation-conditions', {
    conditions,
  });
  return data;
}

export async function recommendRegions(
  conditions: SavedRecommendationConditions,
): Promise<RecommendationRegionsResponse> {
  const { data } = await api.post<RecommendationRegionsResponse>('/recommend/regions', conditions, {
    timeout: 60_000,
  });
  return data;
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


// Re-exports so callers can `import type { User } from '@/features/common/lib/api'` if they
// prefer barreling through the API module rather than `types/api`.
export type {
  FavoriteItem,
  MePatchPayload,
  MeResponse,
  SavedCandidateRegion,
  SavedRecommendationConditions,
  SchoolOptionsResponse,
  UserCandidateRegionsResponse,
  UserRecommendationConditionsResponse,
  User,
  AIAPIKeyStatusResponse,
  AIContextPreferencePatch,
  AIContextPreferenceResponse,
  AIProvider,
};


export async function getAmenitiesBbox(params: {
  bbox: [number, number, number, number];
  categories?: string[];
}): Promise<AmenityBboxResponse> {
  const { data } = await api.get<AmenityBboxResponse>('/amenities/bbox', {
    params: {
      bbox: params.bbox.join(','),
      categories: params.categories?.join(','),
    },
  });
  return data;
}


export async function getMedicalFacilities(params: {
  bbox: [number, number, number, number];
  categories?: string[];
  specialtyGroups?: string[];
  openNow?: boolean;
}): Promise<MedicalFacilitiesResponse> {
  const { data } = await api.get<MedicalFacilitiesResponse>('/medical/facilities', {
    params: {
      bbox: params.bbox.join(','),
      category: params.categories?.join(','),
      specialty_group: params.specialtyGroups?.join(','),
      open_now: params.openNow ? 'true' : undefined,
    },
  });
  return data;
}


export async function getMedicalSpecialtyGroups(params: {
  category?: string;
} = {}): Promise<MedicalSpecialtyGroupsResponse> {
  const { data } = await api.get<MedicalSpecialtyGroupsResponse>('/medical/specialty-groups', {
    params: {
      category: params.category,
    },
  });
  return data;
}
