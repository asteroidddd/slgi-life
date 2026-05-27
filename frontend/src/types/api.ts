// API response types — mirror Django DRF serializers.
// Source of truth:
//   - docs/handoff/20260502-step3-backend-foundation.md
//   - docs/handoff/20260502-step5a-backend-summary.md (AdongSummary, raw scores)
// SPEC sections 9, 10.

/** Single adong score row from GET /api/adongs/scores. */
export interface AdongScore {
  /** URL-safe slug, used in /adong/:slug routes. */
  slug: string;
  /** 행정동 코드 10자리 (행안부). seoul_dongs.geojson properties.adm_cd2 와 매칭. */
  code: string;
  /** 행정동 한국어 이름, e.g. "필동". */
  name: string;
  /** 구 이름, e.g. "중구". */
  gu: string;
  /** Composite weighted score 0~100, two decimals. */
  score: number;
  /** centroid Y (latitude). */
  lat: number;
  /** centroid X (longitude). */
  lng: number;
  /** Raw 전월세 score 0~100 (added in step 5A — SPEC 14.3 client recompute). */
  score_rent: number;
  /** Raw 생활시설 score 0~100. */
  score_amenity: number;
  /** Raw 교통 score 0~100. */
  score_transit: number;
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

/** Response of GET /api/adongs/:slug/detail — full detail page (SPEC 6.3).
 *  Source: docs/handoff/20260502-step6a-backend-detail.md
 */
export interface AdongDetail {
  // 1. Hero
  slug: string;
  name: string;
  gu: string;
  /** Weighted composite 0~100. */
  score: number;
  /** Rule-based one-line summary. */
  summary: string;
  /** Score difference vs Seoul average (baseline 65 in step 6A dummy). */
  vs_seoul_avg_pct: number;
  centroid: { lat: number; lng: number };

  // 2. 부동산 시세
  real_estate: {
    monthly_trend: Array<{
      /** 'YYYY-MM'. */
      month: string;
      /** Average monthly rent (만원). null when fewer than 3 deals that month. */
      villa: number | null;
      /** 다가구 — 옛 multi 통합값에서 분리. */
      dagagu: number | null;
      /** 단독 — 옛 multi 통합값에서 분리. */
      danok: number | null;
      officetel: number | null;
    }>;
    deposit_band_avg: Array<{
      /** '0' | '500' | '1000' | '2000' | '3000+'. */
      band: string;
      /** 만원. */
      avg_monthly_rent: number;
    }>;
    recent_deals: Array<{
      /** 'YYYY-MM-DD'. */
      date: string;
      /** RentDeal.housing_type 한글 raw — 다세대/연립/연립다세대/다가구/단독/오피스텔. */
      type: string;
      area_m2: number;
      /** 만원. */
      deposit: number;
      /** 만원. */
      monthly_rent: number;
    }>;
    /** 자취 시장 KPI — apt 제외, 보증금 5억 이하, 최근 6개월 자취 거래 기준. */
    studio_kpi: {
      /** 평균 환산월세 (만원, 정수). 거래 0건이면 null. */
      avg_converted_rent: number | null;
      /** 최저 보증금 (만원). null = 거래 없음. */
      min_deposit: number | null;
      /** 평균 면적 (m², 1 decimal). null = 거래 없음. */
      avg_area_m2: number | null;
      /** 최근 6개월 자취 거래 건수. */
      recent_count: number;
    };
    /** 유형별 평균 환산월세 (자취 4종, villa/dagagu/danok/officetel 순). */
    type_avg: Array<{
      deal_type: 'villa' | 'dagagu' | 'danok' | 'officetel';
      /** 한글 라벨 — '연립다세대'·'다가구'·'단독'·'오피스텔'. */
      label: string;
      /** 평균 환산월세 (만원). 거래 3건 미만이면 null (회색 처리). */
      avg_converted_rent: number | null;
      /** 해당 유형 거래 건수 (최근 6개월, 자취 필터). */
      count: number;
    }>;
    /** 면적-환산월세 산점도 — 최근 6개월 자취 거래 최대 200건. */
    scatter: Array<{
      deal_type: 'villa' | 'dagagu' | 'danok' | 'officetel';
      area_m2: number;
      converted_rent: number;
    }>;
  };

  // 3. 편의시설 8개 카테고리
  amenities: Array<{
    /** '편의점' | '카페' | '음식점' | '마트' | '병원·약국' | '스터디카페' | '세탁소' | '올리브영'. */
    category: string;
    count: number;
    density_per_km2: number;
    /** 카테고리별 실 카운트 기반 TOP X% (1=최상위, 100=최하위). 산출 불가 시 null. */
    percentile: number | null;
    level: AmenityLevel;
  }>;

  // 4. 교통
  transit: {
    nearest_stations: Array<{
      rank: number;
      name: string;
      line: string;
      walking_min: number;
      walking_distance_m: number;
    }>;
    bus: {
      stop_count: number;
      route_count: number;
    };
  };

  // 5. 비슷한 동네
  similar_dongs: Array<{
    slug: string;
    name: string;
    gu: string;
    /** 0~100 with 1 decimal. */
    similarity_pct: number;
  }>;
}

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

export type ExploreDealType = 'villa' | 'dagagu' | 'danok' | 'officetel' | 'apt';

export type ExplorePeriod = '3m' | '6m' | '12m' | '24m' | 'all';

/** 자취 거래량 필터 공통 base — Explore + MainMap StudioMatch 양쪽 공유 (eng-review #16). */
export interface BaseRentFilters {
  deal_types: ExploreDealType[];
  period: ExplorePeriod;
  deposit_min: number;
  deposit_max: number;
  monthly_min: number;
  monthly_max: number;
  area_min: number;
  area_max: number;
}

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

// -------- Preference learning (SPEC 6.5, 11.4) ---------------------------
// Source: docs/handoff/20260502-step7a-backend-preference.md

/** A single comparison card shown in the preference learning modal.
 *  Backend computes rent_avg / transit_min / amenity_label deterministically.
 */
export interface PairCard {
  slug: string;
  name: string;
  gu: string;
  /** Average monthly rent (만원, score 기반 derived dummy). */
  rent_avg: number;
  /** 평균 환산월세 (만원, 정수). 월세 + 보증금 × 0.005, RentDeal 실거래 기반.
   *  null 또는 undefined → 데이터 부족(거래 적재 안 된 동) 또는 백엔드가 아직
   *  필드를 노출하지 않은 경우. UI는 두 케이스 모두 동일하게 폴백 표기 처리. */
  rent_converted?: number | null;
  /** Walking minutes to nearest subway station. */
  transit_min: number;
  /** Korean human-readable amenity coverage. */
  amenity_label: '충분' | '보통' | '부족';
  /** Composite score @ 33/33/34, two decimals. */
  score: number;
}

/** A pair of adongs the user is asked to choose between. */
export interface PreferencePair {
  left: PairCard;
  right: PairCard;
}

/** Response of GET /api/preference/pairs?count=N. */
export interface PreferencePairsResponse {
  pairs: PreferencePair[];
}

/** Body element for POST /api/preference/submit. */
export interface SubmitComparison {
  /** slug of the chosen (won) adong. */
  won: string;
  /** slug of the rejected (lost) adong. */
  lost: string;
}

/** Response of POST /api/preference/submit.
 *  Integers in 0~100 that sum to exactly 100 — drop straight into Weights.
 */
export interface PreferenceWeightsResponse {
  w_rent: number;
  w_amenity: number;
  w_transit: number;
}

// -------- Compare (SPEC 6.4) ---------------------------------------------
// Source: docs/handoff/20260502-step8a-backend-compare.md

/** Korean-readable amenity coverage label used in the compare table. */
export type CompareAmenityLabel = '충분' | '보통' | '부족';

/** Korean-readable safety label used in the compare table. */
export type CompareSafetyLabel = '높음' | '보통' | '낮음';

/** A single compare-table column (one adong) — GET /api/compare row.
 *  Backend returns rows in the input slug order (preserved for column order).
 */
export interface CompareItem {
  slug: string;
  name: string;
  gu: string;
  /** Weighted composite 0~100 (two decimals). */
  score: number;
  /** Raw average monthly rent in 만원 (정수, dummy: 120 - score_rent). */
  rent_avg: number;
  /** 환산월세 평균 in 만원 (정수). 월세 + 보증금 × 0.005, RentDeal 실거래 기반. null = 데이터 부족. */
  rent_converted_avg: number | null;
  /** Walking minutes to nearest subway station (정수). */
  transit_min: number;
  amenity_label: CompareAmenityLabel;
  safety_label: CompareSafetyLabel;
}

/** Echoed weights — the values the backend actually applied. */
export interface CompareWeights {
  w_rent: number;
  w_amenity: number;
  w_transit: number;
}

/** GET /api/compare?slugs=A,B,C[&w_rent=&w_amenity=&w_transit=] response. */
export interface CompareResponse {
  weights: CompareWeights;
  /** Same order as the input slugs (max 3). */
  adongs: CompareItem[];
}

// -------- Auth + Users (SPEC 6.6, 9 — step 9) -----------------------------
// Source: docs/handoff/20260502-step9a-backend-users.md
//   세션 쿠키 기반 (axios withCredentials: true).
//   카카오/소셜 X — 표준 username/password.

/** Stored preference weights as integer percents (sum = 100, ±1).
 *  Same shape as `Weights` but with backend field names.
 *  Use `mePreferenceToWeights` / `weightsToMePreference` to convert.
 */
export interface MePreference {
  w_rent: number;
  w_amenity: number;
  w_transit: number;
}

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

/** GET /api/users/me — adds the user's saved preference weights. */
export interface MeResponse extends User {
  preference: MePreference;
}

/** POST /api/auth/register body. */
export interface RegisterPayload {
  username: string;
  password: string;
  school?: string;
  year?: number | null;
  nickname?: string;
}

/** POST /api/auth/login body. */
export interface LoginPayload {
  username: string;
  password: string;
}

/** PATCH /api/users/me body — all fields optional. */
export interface MePatchPayload {
  school?: string;
  year?: number | null;
  nickname?: string;
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
//   GET /api/transactions/bbox?bbox=lng1,lat1,lng2,lat2&deal_type=&from=&to=&limit=
//   - Backend filters out geom IS NULL rows (단독다가구 좌표 없음).
//   - Same jibun → same coordinates (privacy: 지번 중심점만, SPEC 14.2).

/** Backend whitelist for the `deal_type` query parameter.
 *  `all` is a sentinel meaning "no filter" — never appears in `RentDealPin.deal_type`.
 */
export type TransactionDealType = 'apt' | 'officetel' | 'villa' | 'dagagu' | 'danok';

/** Same as `TransactionDealType` but with the `all` sentinel for filter UI. */
export type TransactionDealTypeFilter = TransactionDealType | 'all';

/** Single transaction pin row from GET /api/transactions/bbox. */
export interface RentDealPin {
  id: number;
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

/** Response of GET /api/transactions/bbox. */
export interface TransactionsBboxResponse {
  items: RentDealPin[];
  /** True when limit + 1 fetch returned the +1 → next page exists. */
  has_more: boolean;
  /** Display-only count, capped at `limit * 5`. */
  total: number;
  /** True when `total` itself is the cap (real count is higher). */
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

// -------- Kernel score (Phase 2 — POST /api/score/point) -----------------
// Source: docs/handoff/20260503-phase2a-kernel-score.md
//   POST body: { lat, lng, weights:{rent,amenity,transit}, school?:string }
//   - Backend normalizes weights (sum need not be 1.0).
//   - school is optional; backend's SCHOOL_COORDS dict has 16 keys
//     (캠퍼스 정문 좌표). Unknown school → commute_min: null (not an error).

/** Weights body for kernel score. Float values (0~1 range typical, but any
 *  non-negative value works — backend normalizes by sum). */
export interface KernelScoreWeights {
  rent: number;
  amenity: number;
  transit: number;
}

/** Request body for POST /api/score/point. */
export interface KernelScoreRequest {
  lat: number;
  lng: number;
  weights: KernelScoreWeights;
  /** Optional school name (e.g. "동국대"). Unknown name → commute_min null. */
  school?: string;
}

/** Categories returned in `nearest` rows. Subway is special-cased
 *  (carries `line` field). Others mirror Amenity.category. */
export type NearestFacilityCategory =
  | 'subway'
  | 'convenience'
  | 'cafe'
  | 'hospital'
  | 'park'
  | 'mart'
  | 'pharmacy'
  | string;

/** Single nearest facility row in the kernel score response. */
export interface NearestFacility {
  category: NearestFacilityCategory;
  name: string;
  /** Subway only. */
  line?: string;
  /** Walking minutes (rounded). */
  walk_min: number;
  /** Distance in meters (integer). */
  distance_m: number;
}

/** 1km-radius facility counts. Keys are amenity categories. */
export interface RadiusCounts {
  convenience: number;
  cafe: number;
  hospital: number;
  park: number;
  mart: number;
  pharmacy: number;
  /** Forward-compat: backend may add categories. */
  [k: string]: number;
}

/** Debug-only metadata. Phase 2b frontend may ignore. */
export interface KernelScoreMeta {
  dong_slug: string | null;
  dong_name: string | null;
  bus_count_1km: number;
}

/** Response of POST /api/score/point. */
export interface KernelScoreResponse {
  /** 0~100, two decimals. */
  score: number;
  breakdown: {
    rent: number;
    amenity: number;
    transit: number;
  };
  nearest: NearestFacility[];
  radius_counts: RadiusCounts;
  /** Walking + train minutes to school (haversine + 22 km/h). null when
   *  school omitted or unknown. */
  commute_min: number | null;
  _meta?: KernelScoreMeta;
}

export interface SchoolOption {
  id: string;
  name: string;
  school_type: string;
}

export interface SchoolOptionsResponse {
  schools: SchoolOption[];
}

/** Fallback only. Runtime school selects are loaded from the Univ DB. */
export const KERNEL_SCHOOL_OPTIONS = [
  '동국대',
  '한양대',
  '고려대',
  '연세대',
  '서강대',
  '이화여대',
  '홍익대',
  '서울대',
  '중앙대',
  '건국대',
  '성균관대',
  '경희대',
  '한국외대',
  '서울시립대',
] as const;
export type KernelSchool = (typeof KERNEL_SCHOOL_OPTIONS)[number];

// -------- AI Agent (POST /api/agent/query) --------------------------------

export interface AgentQueryRequest {
  question: string;
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
  columns?: Record<string, string | number | boolean | null>;
}

export interface AgentVisualization {
  type: 'bar' | 'line' | 'table' | 'none' | string;
  title: string;
  unit: string;
  data: AgentVisualizationDatum[];
}

export interface AgentQueryResponse {
  answer: string;
  query_type: 'recommendation' | 'info' | 'none' | string;
  route: 'db' | 'direct' | 'blocked' | string;
  neighborhoods: AgentNeighborhood[];
  visualizations: AgentVisualization[];
  elapsed_sec: number;
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
