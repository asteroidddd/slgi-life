// API response types — mirror Django DRF serializers.
// Source of truth:
//   - docs/handoff/20260502-step3-backend-foundation.md
//   - docs/handoff/20260502-step5a-backend-summary.md (AdongSummary, raw scores)
// SPEC sections 9, 10.

/** Single adong score row from GET /api/heatmap/adongs/scores. */
export interface AdongScore {
  /** URL-safe slug used by map selection. */
  slug: string;
  /** 행정동 코드 10자리 (행안부). seoul_dongs.geojson properties.adm_cd2 와 매칭. */
  code: string;
  /** 행정동 한국어 이름, e.g. "필동". */
  name: string;
  /** 구 이름, e.g. "중구". */
  gu: string;
  /** Composite score 0~100. */
  score: number;
  score_total?: number;
  /** centroid Y (latitude). */
  lat: number;
  /** centroid X (longitude). */
  lng: number;
  /** Raw 전월세 score 0~100 (added in step 5A — SPEC 14.3 client recompute). */
  score_rent: number | null;
  /** Raw 생활시설 score 0~100. */
  score_amenity: number;
  /** Raw 교통 score 0~100. */
  score_transit: number;
  /** 구 단위 안전 지표를 동에 매핑한 score 0~100. */
  score_safety: number;
}

export interface DashboardRegionIntro {
  type: 'adong' | 'ldong';
  code: string;
  slug: string;
  gu_name: string;
  dong_name: string;
  intro: string;
}

/** Nearest subway station shown in the adong panel (SPEC 6.2). */
export interface NearestStation {
  rank?: number;
  name: string;
  line: string;
  walking_min: number;
  walking_distance_m?: number;
}

/** Three-level rating for amenity coverage (SPEC 6.2 핵심 지표). */
export type AmenityLevel = 'sufficient' | 'normal' | 'lacking';

/** Three-level rating for safety (SPEC 6.2 핵심 지표). */
export type SafetyLevel = 'high' | 'mid' | 'low';

/** Response of GET /api/adongs/:slug/summary — drives the slide-in adong panel.
 *  Source: docs/handoff/20260502-step5a-backend-summary.md
 */
export interface AdongSummary {
  slug: string;
  name: string;
  gu: string;
  /** Weighted composite 0~100, two decimals. */
  score: number;
  /** Rule-based one-line summary (Korean). */
  summary: string;
  /** Average monthly rent in 만원 (정수). */
  rent_avg: number;
  /** Average converted monthly rent per m², in 만원/m². */
  rent_per_m2_avg: number | null;
  nearest_station: NearestStation;
  nearest_stations?: NearestStation[];
  amenity_level: AmenityLevel;
  safety_level: SafetyLevel;
}

/** User-controlled weights for the main map sidebar (SPEC 6.1).
 *  Values are integers 0~100. Sum must equal 100.
 *  Backend tolerates ±1 sum drift (rounding); we still normalize on the client.
 */
export interface Weights {
  rent: number;
  amenity: number;
  transit: number;
}

/** Default weights on first load (SPEC 6.1). */
export const DEFAULT_WEIGHTS: Weights = {
  rent: 33,
  amenity: 33,
  transit: 34,
};

// -------- Dashboard Phase 2 — Population + Gu Metrics --------------------

/** Single time-series row from GET /api/adongs/:slug/population. */
export interface PopulationTrendRow {
  date: string;
  total_population: number;
  household_count: number;
  male_population: number;
  female_population: number;
}

/** Response of GET /api/adongs/:slug/population. */
export interface AdongPopulationResponse {
  adong: { slug: string; name: string; gu: string };
  latest: PopulationTrendRow | null;
  trend: PopulationTrendRow[];
}

/** Single metric value within the gu-metrics response. */
export interface GuMetricValue {
  value: number | null;
  /** ISO date 'YYYY-MM-DD'. metric_code별로 적재 주기가 달라 응답에 코드별 date가 들어온다. */
  date?: string | null;
  name: string;
  unit: string;
  category: string;
  /** 25개 자치구 중 값이 큰 순으로 1위. value=null이면 null. 동률은 같은 rank. */
  rank_in_seoul?: number | null;
  /** 그 date에 데이터를 가진 구 수 (일반적으로 25). */
  gu_count?: number;
  /** 25개 자치구 산술 평균 (null 제외). SeoulMetric raw와 의미 다름. */
  gu_avg?: number | null;
}

/** Seoul average row in gu-metrics response. */
export interface SeoulAvgValue {
  value: number | null;
  date?: string | null;
}

/** Response of GET /api/adongs/:slug/gu-metrics. */
export interface AdongGuMetricsResponse {
  adong: { slug: string; name: string; gu: string };
  gu_code: string;
  gu_name: string;
  /** Deprecated — top-level date removed in 2026-05-13 backend update.
   *  Each metric carries its own date now (metrics[code].date). Kept optional
   *  for backwards-compat only; new code should reference per-metric dates. */
  date?: string | null;
  metrics: Record<string, GuMetricValue>;
  seoul_avg: Record<string, SeoulAvgValue>;
}

/** Single time-series point in the gu-metrics series response.
 *  `value` may be null for missing entries — chart layer uses connectNulls. */
export interface GuMetricSeriesPoint {
  date: string;
  value: number | null;
}

/** A single metric series (one metric_code) in the gu-metrics series response. */
export interface GuMetricSeries {
  name: string;
  unit: string;
  category: string;
  points: GuMetricSeriesPoint[];
  /** series의 가장 최신 non-null point 기준 25구 중 순위. 데이터 없으면 null. */
  current_rank?: {
    rank: number;
    total: number;
    value: number | null;
    date: string;
  } | null;
}

/** Response of GET /api/adongs/:slug/gu-metrics/series?codes=...&years=N.
 *  `series` keyed by metric_code; same keys mirrored under `seoul_series`
 *  (Seoul-wide averages). All requested codes are always present (empty
 *  points array when no data) — simplifies the frontend branching. */
export interface GuMetricSeriesResponse {
  adong: { slug: string; name: string; gu: string };
  gu_code: string;
  gu_name: string;
  series: Record<string, GuMetricSeries>;
  seoul_series: Record<string, { points: GuMetricSeriesPoint[] }>;
  /** date별 25구 산술 평균 시계열. seoul_series와 alignment 동일. 비교용으로 권장. */
  gu_avg_series?: Record<string, { points: GuMetricSeriesPoint[] }>;
}

// -------- Dashboard Section C — Transit Congestion (SPEC 4.4 Section C) ----
// GET /api/adongs/:slug/transit-congestion
// Backend computes congestion patterns from SubwayCongestion (TOP3 nearby
// stations, averaged) + BusCongestion (all BusStops mapped to the adong).
// Personality estimate derived from morning_peak / midday / evening_peak /
// weekend averages. See STATE.md Backend section for full schema notes.

/** Single hour bucket (0~23) congestion value. `null` for missing slots. */
export interface CongestionPoint {
  hour: number;
  /** Raw congestion (not normalized). Subway range ~0~67 (occasional spikes to
   *  ~390); bus range typically 0~1+. Frontend renders both as-is with
   *  connectNulls on the chart layer. */
  congestion: number | null;
}

/** Response of GET /api/adongs/:slug/transit-congestion. */
export interface TransitCongestionResponse {
  adong: { slug: string; name: string; gu: string };
  subway: {
    /** TOP 3 nearest stations whose congestion is averaged for the curves. */
    stations: { name: string; line: string }[];
    by_day: {
      평일: CongestionPoint[];
      토요일: CongestionPoint[];
      일요일: CongestionPoint[];
    };
  };
  bus: {
    /** Number of BusStops mapped to the adong (sample size). 0 → no bus data. */
    stop_count: number;
    by_pattern: {
      평일: CongestionPoint[];
      주말: CongestionPoint[];
    };
  };
  personality: {
    label: '주거 중심' | '상업·업무 중심' | '유동인구 많음' | null;
    reason: string | null;
    /** Pattern aggregates used to derive the label (0~range). null when data
     *  for the corresponding bucket is missing. */
    scores: {
      morning_peak: number | null;
      midday: number | null;
      evening_peak: number | null;
      weekend: number | null;
    };
  };
}


// -------- Dashboard Section B — Parks (SPEC 4.4 Section B) --------------

/** Single park row in GET /api/adongs/:slug/parks. */
export interface AdongPark {
  id: string;
  name: string;
  /** 공원 분류 (예: 근린공원, 어린이공원, 도시자연공원). */
  category: string;
  /** 면적 (m²). null 가능. */
  area_m2: number | null;
  lat: number | null;
  lng: number | null;
  /** 행정동 중심점 ↔ 공원 위치 거리 (미터). 좌표 누락 시 null. */
  distance_m: number | null;
}

/** Response of GET /api/adongs/:slug/parks.
 *  RDS 원본에 동일 공원 중복 행이 있어 클라이언트에서 id 기준 dedupe 필요. */
export interface AdongParksResponse {
  adong: { slug: string; name: string; gu: string };
  count: number;
  parks: AdongPark[];
}

export interface RentConversionRateResponse {
  annual_rate: number;
  monthly_rate: number;
  source: string;
  unit: 'percent_per_year';
}

export type RentListingType = 'apartment' | 'officetel' | 'villa_house';

export interface RentListingAnalysisRequest {
  address: string;
  area_m2: number;
  housing_type: RentListingType;
  deposit: number;
  monthly_rent: number;
  include_adjacent: boolean;
}

export interface RentListingAnalysisResponse {
  status: 'ok' | 'no_data';
  input: {
    address: string;
    area_m2: number;
    deposit: number;
    monthly_rent: number;
    converted_monthly_rent: number;
    rent_per_area: number;
    housing_type: RentListingType | string;
    housing_type_label: string;
    include_adjacent: boolean;
  };
  region: {
    code: string;
    slug: string;
    gu_name: string;
    dong_name: string;
    name: string;
    address_source: Record<string, unknown>;
    included_regions: Array<{ code: string; gu_name: string; dong_name: string; slug: string }>;
  };
  comparison: {
    scope: string;
    lookback_days: number;
    decay_days: number;
    housing_type_label: string;
    housing_types: string[];
    sample_count: number;
    effective_sample_count: number;
    confidence: 'high' | 'medium' | 'low';
    confidence_label: string;
    min_contract_date: string | null;
    max_contract_date: string | null;
    type_counts: Record<string, number>;
  };
  stats: {
    q20: number | null;
    q40: number | null;
    median: number | null;
    q60: number | null;
    q80: number | null;
    weighted_percentile: number | null;
    delta_to_median_pct: number | null;
  };
  verdict: {
    label: string;
    tone: 'good' | 'info' | 'bad' | string;
    description: string;
    summary: string;
  };
  basis: {
    annual_rate: number;
    monthly_rate: number;
    source: string;
    unit: string;
    period: string;
    weight_formula: string;
  };
  disclaimer: string;
}

// -------- Auth + Users (SPEC 6.6, 9 — step 9) -----------------------------
// Source: docs/handoff/20260502-step9a-backend-users.md
//   세션 쿠키 기반 (axios withCredentials: true).
//   카카오/소셜 X — 표준 username/password.

/** Bare user — used in many response shapes. */
export interface User {
  id: number;
  username: string;
  /** May be the empty string; backend falls back to username on GET /me. */
  nickname: string;
  /** May be the empty string. */
  school: string;
  /** Null when not provided. */
  year: number | null;
}

/** GET /api/users/me. */
export interface MeResponse extends User {
  email: string;
  auth_provider: 'kakao' | 'password';
  address: string;
  school_lat: number | null;
  school_lng: number | null;
  home_lat: number | null;
  home_lng: number | null;
  address_geocode_status: string;
  address_geocode_error: string;
}

/** POST /api/auth/register body. */
export interface RegisterPayload {
  username: string;
  password: string;
  school?: string;
  year?: number | null;
  nickname?: string;
  address?: string;
  terms_agreed: boolean;
}

/** POST /api/auth/login body. */
export interface LoginPayload {
  username: string;
  password: string;
}

/** PATCH /api/users/me body — all fields optional. */
export interface MePatchPayload {
  email?: string;
  school?: string;
  year?: number | null;
  nickname?: string;
  address?: string;
}

/** Single row of GET /api/users/me/favorites and the POST response. */
export interface FavoriteItem {
  slug: string;
  name: string;
  gu: string;
  /** 0~100, applied with the user's saved weights. */
  score: number;
  /** ISO 8601 KST. */
  created_at: string;
}

export type SavedCandidateRegionLevel = 'adong' | 'ldong';
export type SavedCandidateSource = 'conditions' | 'map' | 'detail';

export interface SavedCandidateRegion {
  regionLevel: SavedCandidateRegionLevel;
  slug: string;
  code?: string;
  gu: string;
  name: string;
  lat?: number;
  lng?: number;
  score?: number | null;
  score_rent?: number | null;
  score_transit?: number | null;
  score_amenity?: number | null;
  score_safety?: number | null;
  source: SavedCandidateSource;
  addedAt: number;
}

export interface UserCandidateRegionsResponse {
  max_items: number;
  items: SavedCandidateRegion[];
}

export interface NeighborhoodCompareMetric {
  key: string;
  label: string;
  value: string | number | null;
  unit: string;
  tone: 'good' | 'bad' | 'warn' | 'info' | string;
  badge: string;
  description: string;
}

export interface NeighborhoodCompareQuickTake {
  label: string;
  tone: 'good' | 'bad' | 'warn' | 'info' | string;
}

export interface NeighborhoodCompareSection {
  headline: string;
  summary: string;
  quicktakes: NeighborhoodCompareQuickTake[];
  metrics: NeighborhoodCompareMetric[];
  station_items?: Array<{
    name?: string;
    distance_m?: number | null;
    lines?: string[];
  }>;
  station_names?: string[];
  category_items?: Array<Record<string, unknown>>;
  grade_items?: Array<Record<string, unknown>>;
}

export interface NeighborhoodCompareItem {
  key: string;
  regionLevel: SavedCandidateRegionLevel;
  code: string;
  slug: string;
  gu: string;
  name: string;
  lat: number | null;
  lng: number | null;
  area_km2: number | null;
  intro: string;
  computed_at: string;
  commute: {
    university: {
      id: string;
      name: string;
    } | null;
    travel_minutes: number | null;
  };
  scores: {
    total: number | null;
    rent: number | null;
    transit: number | null;
    amenity: number | null;
    safety: number | null;
    rank_total: number | null;
    rank_rent: number | null;
    rank_transit: number | null;
    rank_amenity: number | null;
    rank_safety: number | null;
  };
  sections: {
    rent: NeighborhoodCompareSection;
    transit: NeighborhoodCompareSection;
    infra: NeighborhoodCompareSection;
    safety: NeighborhoodCompareSection;
  };
}

export interface NeighborhoodCompareResponse {
  max_items: number;
  items: NeighborhoodCompareItem[];
  missing: Array<{
    regionLevel: SavedCandidateRegionLevel;
    slug: string;
    reason: string;
  }>;
}

export interface NeighborhoodCommuteTimeResponse {
  regionLevel: SavedCandidateRegionLevel;
  slug: string;
  code: string;
  gu: string;
  name: string;
  university: {
    id: string;
    name: string;
  };
  travel_minutes: number | null;
}

export type SavedRecommendationPriority = 'budget' | 'transport';

export interface SavedRecommendationConditions {
  deposit: number;
  monthlyRent: number;
  areaM2: number | null;
  facilities: string[];
  universityId: string;
  universityName: string;
  maxCommuteMinutes: number;
  priority: SavedRecommendationPriority;
}

export interface UserRecommendationConditionsResponse {
  conditions: SavedRecommendationConditions | null;
}

export interface RecommendationRegionCandidate extends AdongScore {
  rank: number;
  region_level: 'adong' | 'ldong';
  rent_metric: number | null;
  rent_metric_label: string;
  travel_minutes: number | null;
}

export interface RecommendationRegionsResponse {
  adongs: RecommendationRegionCandidate[];
  ldongs: RecommendationRegionCandidate[];
  total: number;
  basis: {
    conversion_rate_period: string | null;
    conversion_monthly_rate: number;
    facility_match: 'all_selected';
    limit: number;
  };
}

/** Shape of 4xx error payloads from the auth/users routes (step9a).
 *  Field arrays come from DRF serializers; `detail` from custom messages.
 */
export interface ApiErrorDetail {
  detail?: string;
  username?: string | string[];
  password?: string | string[];
  slug?: string | string[];
  weights?: string | string[];
  w_rent?: string | string[];
  w_amenity?: string | string[];
  w_transit?: string | string[];
}

/** WGS84 bbox in (lng, lat) order matching backend query string format. */
export interface Bbox {
  lng1: number;
  lat1: number;
  lng2: number;
  lat2: number;
}

export interface SchoolOption {
  id: string;
  name: string;
  school_type: string;
}

export interface SchoolOptionsResponse {
  schools: SchoolOption[];
}

// -------- AI Agent (POST /api/agent/query) --------------------------------

export interface AgentQueryRequest {
  question: string;
  conversation_id?: string;
}

export interface AgentNeighborhood {
  rank: number;
  ldong_name: string;
  gu_name: string;
  one_liner: string;
  data_summary: string;
}

export interface AgentVisualizationDatum {
  label: string;
  value?: number;
  is_baseline?: boolean;
  lat?: number;
  lng?: number;
  columns?: Record<string, string | number | boolean | null>;
}

export interface AgentVisualization {
  type: 'bar' | 'line' | 'table' | 'none' | string;
  title: string;
  unit: string;
  data: AgentVisualizationDatum[];
}

export interface AgentQueryResponse {
  conversation_id: string;
  answer: string;
  query_type: 'recommendation' | 'info' | 'none' | string;
  route: 'db' | 'direct' | 'blocked' | string;
  neighborhoods: AgentNeighborhood[];
  visualizations: AgentVisualization[];
  elapsed_sec: number;
  provider?: {
    used_provider: AIProvider | string;
    fallback_used: boolean;
    failed_provider: AIProvider | string | null;
    fallback_reason: string;
  };
}

export type AIProvider = 'mindlogic' | 'openai';

export interface AIAPIKeyStatus {
  provider: AIProvider;
  configured: boolean;
  priority: number | null;
  masked_key: string;
  unlocked: boolean;
}

export interface AIAPIKeyStatusResponse {
  keys: AIAPIKeyStatus[];
  unlock_ttl_seconds: number;
  can_use_demo?: boolean;
}

export interface AIContextPreferenceResponse {
  share_school_with_ai: boolean;
  share_home_location_with_ai: boolean;
  school_available: boolean;
  home_location_available: boolean;
}

export interface AIContextPreferencePatch {
  share_school_with_ai?: boolean;
  share_home_location_with_ai?: boolean;
}

// -------- Map search -------------------------------------------------------

export interface MapSearchItem {
  id: string;
  source: 'vworld';
  type: 'place' | 'address' | 'district' | 'road' | string;
  name: string;
  label: string;
  address: string;
  lat: number;
  lng: number;
}

export interface MapSearchResponse {
  items: MapSearchItem[];
}

export interface AmenityBboxItem {
  id: number;
  category: string;
  name: string;
  lat: number | null;
  lng: number | null;
  source_table: string;
  source_id: string;
}

export interface AmenityBboxResponse {
  bbox: [number, number, number, number];
  categories: string[];
  limit: number;
  limit_scope?: 'category';
  count: number;
  items: AmenityBboxItem[];
}

export type MedicalCategoryKey = 'hospital' | 'dental' | 'pharmacy' | 'emergency';

export interface MedicalFacilityItem {
  hpid: string;
  category: MedicalCategoryKey | string;
  type: string;
  name: string;
  address: string;
  tel1: string | null;
  lat: number | null;
  lng: number | null;
  is_emergency: boolean;
  distance_m: number | null;
}

export interface MedicalFacilitiesResponse {
  categories: string[];
  specialties: string[];
  specialty_groups?: string[];
  open_now: boolean;
  bbox: [number, number, number, number] | null;
  radius: number | null;
  limit: number | null;
  count: number;
  items: MedicalFacilityItem[];
}

export interface MedicalSpecialtyGroupItem {
  name: string;
  rows: number | null;
  facilities: number | null;
  description?: string;
}

export interface MedicalSpecialtyGroupsResponse {
  count: number;
  items: MedicalSpecialtyGroupItem[];
}
