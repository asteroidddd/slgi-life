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

// -------- Explore (Phase 4.8 — 자취 시세 BI 대시보드) --------------------
// GET /api/adongs/:slug/explore?<filters>

export type ExploreDealType = 'yeonlip' | 'dasedae' | 'yeonlip_dasedae' | 'dagagu' | 'danok' | 'danok_dagagu' | 'officetel' | 'apt';

export type ExplorePeriod = '3m' | '6m' | '12m' | '24m' | 'all';

/** 자취 거래량 필터 공통 base — Explore + MainMap StudioMatch 양쪽 공유 (eng-review #16). */
export interface BaseRentFilters {
  deal_types: ExploreDealType[];
  period: ExplorePeriod;
  filter_mode: RentFilterMode;
  deposit_min: number;
  deposit_max: number;
  monthly_min: number;
  monthly_max: number;
  area_min: number;
  area_max: number;
}

export type RentFilterMode = 'converted' | 'raw';

export type ExploreSort =
  | 'date_desc'
  | 'date_asc'
  | 'deposit_desc'
  | 'deposit_asc'
  | 'monthly_desc'
  | 'monthly_asc'
  | 'converted_desc'
  | 'converted_asc'
  | 'area_desc'
  | 'area_asc';

/** 사용자가 조작하는 필터 상태. URL 쿼리스트링과 1:1 동기화. */
export interface ExploreFilters extends BaseRentFilters {
  page: number;
  page_size: number;
  sort: ExploreSort;
}

export interface ExploreKpi {
  count: number;
  avg_converted_rent: number | null;
  min_deposit: number | null;
  avg_area_m2: number | null;
}

export interface ExploreTypeAvgRow {
  deal_type: ExploreDealType;
  label: string;
  avg_converted_rent: number | null;
  count: number;
}

export interface ExploreScatterPoint {
  deal_type: ExploreDealType;
  area_m2: number;
  converted_rent: number;
}

export interface ExploreDepositBandRow {
  band: string;
  count: number;
  avg_monthly_rent: number;
}

export interface ExploreMonthlyTrendRow {
  month: string;
  villa: number | null;
  dagagu: number | null;
  danok: number | null;
  officetel: number | null;
}

export interface ExploreDealItem {
  date: string;
  type: string;
  deal_type: ExploreDealType;
  area_m2: number;
  deposit: number;
  monthly_rent: number;
  converted_rent: number;
  house_name: string;
  build_year: number | null;
  floor: number | null;
}

export interface ExploreDealsPage {
  items: ExploreDealItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ExploreResponse {
  adong: { slug: string; code: string; name: string; gu: string };
  filters_applied: ExploreFilters;
  kpi: ExploreKpi;
  type_avg: ExploreTypeAvgRow[];
  scatter: ExploreScatterPoint[];
  deposit_band: ExploreDepositBandRow[];
  monthly_trend: ExploreMonthlyTrendRow[];
  deals: ExploreDealsPage;
}

// -------- Studio Match (Phase 5 — 메인 지도 자취 거래량 분포) ------------
// GET /api/adongs/match-counts?<filters>
// GET /api/adongs/:slug/match-detail?<filters>
//
// 데이터 = 국토부 실거래 최근 N개월 (현재 매물 재고 X, 자취·원룸 거래량 분포).

export interface MatchFilters extends BaseRentFilters {
  /** Converted monthly rent range (만원). Client-side main-map filter. */
  converted_min: number;
  converted_max: number;
}

export interface MatchCountItem {
  /** 행정동 코드 10자리 (GeoJSON adm_cd2 매칭). */
  code: string;
  slug: string;
  /** 필터 통과 거래 건수. */
  count: number;
  /** 0~100. min_sample 미만이면 0. */
  ratio: number;
  /** false 면 NO_DATA 색 (응답 분기 — eng-review #4). */
  has_data: boolean;
}

export interface MatchCountsResponse {
  filters_applied: MatchFilters;
  total_matched: number;
  /** 표본이 이 미만인 동은 ratio=0 (eng-review #3). */
  min_sample: number;
  adongs: MatchCountItem[];
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

export interface MatchDetailResponse {
  /** 동 메타. */
  adong: { slug: string; code: string; name: string; gu: string };
  filters_applied: MatchFilters;
  /** 이 동의 필터 통과 거래 수. */
  count: number;
  /** 평균 환산월세 (만원, 정수). null = 거래 부족. */
  avg_converted_rent: number | null;
  /** 평균 보증금 (만원, 정수). null = 거래 부족. */
  avg_deposit: number | null;
  /** 매칭률 (%, 1 decimal). 같은 동·같은 기간·같은 거래유형 set 전체 거래 대비. null = denominator 0. */
  match_ratio: number | null;
  /** 매칭률 분모 (같은 동/기간/유형 set 전체 거래수). */
  period_total: number;
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

// -------- Transactions (Phase 1 — main map raw pin layer) ----------------
// Source: docs/handoff/20260503-phase1a-transactions-api.md
//   GET /api/transactions/bbox?bbox=lng1,lat1,lng2,lat2&deal_type=&from=&to=
//   - Backend filters out geom IS NULL rows (단독다가구 좌표 없음).
//   - Same jibun → same coordinates (privacy: 지번 중심점만, SPEC 14.2).

/** Backend whitelist for the `deal_type` query parameter.
 *  `all` is a sentinel meaning "no filter" — never appears in `RentDealPin.deal_type`.
 */
export type TransactionDealType = 'apt' | 'officetel' | 'yeonlip' | 'dasedae' | 'yeonlip_dasedae' | 'villa' | 'dagagu' | 'danok' | 'danok_dagagu';

/** Same as `TransactionDealType` but with the `all` sentinel for filter UI. */
export type TransactionDealTypeFilter = TransactionDealType | 'all';

/** Single transaction pin row from GET /api/transactions/bbox. */
export interface RentDealPin {
  id: string;
  /** 'YYYY-MM-DD'. */
  date: string;
  deal_type: TransactionDealType;
  /** Square meters (소수 가능). */
  area_m2: number;
  /** Deposit (만원). */
  deposit: number;
  /** Monthly rent (만원). 0 → 전세. */
  monthly_rent: number;
  /** 환산월세 (만원, 정수). 보증금을 월세로 환산해 합산: monthly_rent + deposit × 0.005.
   *  Backend가 RentDealPinSerializer에서 직접 계산해 내려준다 (lib/rent.ts와 동일 계수). */
  converted_rent: number;
  /** WGS84 latitude. */
  lat: number;
  /** WGS84 longitude. */
  lng: number;
  /** 지번 (e.g., "90-24"). */
  jibun: string;
  /** 행정동 한국어 이름 (e.g., "광희동"). */
  dong_name: string;
  /** 구 이름 (e.g., "중구"). */
  gu: string;
}

export type RentDealCacheTypeCode = 'A' | 'O' | 'Y' | 'D' | 'V' | 'M' | 'H' | 'S';

export type RentDealCacheRow = [
  id: string,
  t: RentDealCacheTypeCode,
  d: number,
  m: number,
  c: number,
  a: number | null,
  lng: number | null,
  lat: number | null,
  dt: number,
];

export interface RentDealCacheResponse {
  version: number;
  ttl_seconds: number;
  columns: ['id', 't', 'd', 'm', 'c', 'a', 'lng', 'lat', 'dt'];
  type_map: Record<RentDealCacheTypeCode, ExploreDealType>;
  rows: RentDealCacheRow[];
}

export type RentDealSummaryKind = 'ldong' | 'grid';

export interface RentDealSummaryPin {
  kind: RentDealSummaryKind;
  id: string;
  label: string;
  gu_name?: string;
  deal_type: ExploreDealType;
  area_m2: number | null;
  deposit: number;
  monthly_rent: number;
  converted_rent: number;
  count: number;
  lat: number;
  lng: number;
  contract_ymd: number;
}

export type RentDealLdongSummaryRow = [
  ldong_code: string,
  gu_name: string,
  ldong_name: string,
  avg: number,
  count: number,
  lng: number,
  lat: number,
];

export interface RentDealLdongSummaryResponse {
  version: number;
  ttl_seconds: number;
  columns: ['ldong_code', 'gu_name', 'ldong_name', 'avg', 'count', 'lng', 'lat'];
  filters_applied: MatchFilters;
  rows: RentDealLdongSummaryRow[];
}

export type RentDealGridSummaryRow = [
  grid_id: string,
  gu_code: string,
  gu_name: string,
  avg: number,
  count: number,
  lng: number,
  lat: number,
];

export interface RentDealGridSummaryResponse {
  version: number;
  ttl_seconds: number;
  grid_size_m: number;
  columns: ['grid_id', 'gu_code', 'gu_name', 'avg', 'count', 'lng', 'lat'];
  filters_applied: MatchFilters;
  rows: RentDealGridSummaryRow[];
}

export interface RentDealGuCodeItem {
  gu_code: string;
  gu_name: string;
}

export interface RentDealGuCodesResponse {
  version: number;
  ttl_seconds: number;
  items: RentDealGuCodeItem[];
}

export interface RentDealCachePin {
  id: string;
  deal_type: ExploreDealType;
  area_m2: number | null;
  deposit: number;
  monthly_rent: number;
  converted_rent: number;
  lat: number;
  lng: number;
  contract_ymd: number;
}

/** Response of GET /api/transactions/bbox. */
export interface TransactionsBboxResponse {
  items: RentDealPin[];
  /** Limit is no longer applied; kept for response compatibility. */
  has_more: boolean;
  /** Display-only count of returned rows. */
  total: number;
  /** Limit is no longer applied; kept for response compatibility. */
  has_more_total: boolean;
}

/** WGS84 bbox in (lng, lat) order matching backend query string format. */
export interface Bbox {
  lng1: number;
  lat1: number;
  lng2: number;
  lat2: number;
}

/** Filters applied to /api/transactions/bbox. */
export interface TransactionFilters {
  deal_type: TransactionDealTypeFilter;
  /** ISO date 'YYYY-MM-DD' (inclusive lower bound) or null. */
  from: string | null;
  /** ISO date 'YYYY-MM-DD' (inclusive upper bound) or null. */
  to: string | null;
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
