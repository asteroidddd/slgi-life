// React Query hook + URL state helpers for /adong/:slug/explore (Phase 4.8).
//
// 필터 상태는 URL 쿼리스트링과 1:1 동기화 — 새로고침/공유 시에도 동일 화면.
// 필터 변경 → URL push → query refetch.

import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import { getAdongExplore } from '@/lib/api';
import type {
  ExploreDealType,
  ExploreFilters,
  ExplorePeriod,
  ExploreResponse,
  ExploreSort,
} from '@/types/api';

const ALL_DEAL_TYPES: ExploreDealType[] = ['villa', 'dagagu', 'danok', 'officetel', 'apt'];
const STUDIO_DEFAULT: ExploreDealType[] = ['villa', 'dagagu', 'danok', 'officetel'];
const PERIOD_VALUES: ExplorePeriod[] = ['3m', '6m', '12m', '24m', 'all'];
const SORT_VALUES: ExploreSort[] = [
  'date_desc',
  'date_asc',
  'deposit_desc',
  'deposit_asc',
  'monthly_desc',
  'monthly_asc',
  'converted_desc',
  'converted_asc',
  'area_desc',
  'area_asc',
];

export const DEFAULT_EXPLORE_FILTERS: ExploreFilters = {
  deal_types: STUDIO_DEFAULT,
  period: '6m',
  deposit_min: 0,
  deposit_max: 50_000,
  monthly_min: 0,
  monthly_max: 300,
  area_min: 10,
  area_max: 100,
  page: 1,
  page_size: 20,
  sort: 'date_desc',
};

function parseInt32(raw: string | null, fallback: number): number {
  if (raw == null || raw === '') return fallback;
  const v = Number.parseInt(raw, 10);
  return Number.isFinite(v) ? v : fallback;
}

function parseEnum<T extends string>(
  raw: string | null,
  allowed: T[],
  fallback: T,
): T {
  if (raw && (allowed as string[]).includes(raw)) return raw as T;
  return fallback;
}

function parseDealTypes(raw: string | null): ExploreDealType[] {
  if (!raw) return STUDIO_DEFAULT;
  const items = raw
    .split(',')
    .map((s) => s.trim())
    .filter((s): s is ExploreDealType => (ALL_DEAL_TYPES as string[]).includes(s));
  return items.length > 0 ? items : STUDIO_DEFAULT;
}

/** URL 쿼리스트링 → ExploreFilters. 검증 실패는 default 로 폴백. */
export function readFiltersFromSearch(search: URLSearchParams): ExploreFilters {
  return {
    deal_types: parseDealTypes(search.get('deal_types')),
    period: parseEnum<ExplorePeriod>(search.get('period'), PERIOD_VALUES, '6m'),
    deposit_min: parseInt32(search.get('deposit_min'), DEFAULT_EXPLORE_FILTERS.deposit_min),
    deposit_max: parseInt32(search.get('deposit_max'), DEFAULT_EXPLORE_FILTERS.deposit_max),
    monthly_min: parseInt32(search.get('monthly_min'), DEFAULT_EXPLORE_FILTERS.monthly_min),
    monthly_max: parseInt32(search.get('monthly_max'), DEFAULT_EXPLORE_FILTERS.monthly_max),
    area_min: parseInt32(search.get('area_min'), DEFAULT_EXPLORE_FILTERS.area_min),
    area_max: parseInt32(search.get('area_max'), DEFAULT_EXPLORE_FILTERS.area_max),
    page: Math.max(1, parseInt32(search.get('page'), 1)),
    page_size: Math.min(
      100,
      Math.max(1, parseInt32(search.get('page_size'), DEFAULT_EXPLORE_FILTERS.page_size)),
    ),
    sort: parseEnum<ExploreSort>(search.get('sort'), SORT_VALUES, 'date_desc'),
  };
}

/** ExploreFilters → URLSearchParams (default 와 같은 값은 omit 해서 URL 짧게). */
export function writeFiltersToSearch(f: ExploreFilters): URLSearchParams {
  const sp = new URLSearchParams();
  const d = DEFAULT_EXPLORE_FILTERS;
  if (f.deal_types.join(',') !== d.deal_types.join(',')) {
    sp.set('deal_types', f.deal_types.join(','));
  }
  if (f.period !== d.period) sp.set('period', f.period);
  if (f.deposit_min !== d.deposit_min) sp.set('deposit_min', String(f.deposit_min));
  if (f.deposit_max !== d.deposit_max) sp.set('deposit_max', String(f.deposit_max));
  if (f.monthly_min !== d.monthly_min) sp.set('monthly_min', String(f.monthly_min));
  if (f.monthly_max !== d.monthly_max) sp.set('monthly_max', String(f.monthly_max));
  if (f.area_min !== d.area_min) sp.set('area_min', String(f.area_min));
  if (f.area_max !== d.area_max) sp.set('area_max', String(f.area_max));
  if (f.page !== d.page) sp.set('page', String(f.page));
  if (f.page_size !== d.page_size) sp.set('page_size', String(f.page_size));
  if (f.sort !== d.sort) sp.set('sort', f.sort);
  return sp;
}

export interface UseExploreFiltersReturn {
  filters: ExploreFilters;
  /** 부분 갱신 — 갱신된 필드를 제외한 나머지는 유지. page 초기화는 호출자 책임. */
  patch: (delta: Partial<ExploreFilters>) => void;
  /** 페이지네이션 등 page-only 변경. 다른 필드는 유지. */
  setPage: (page: number) => void;
  /** 모든 필터 default 로 리셋. */
  reset: () => void;
}

/** URL 쿼리스트링과 동기화된 필터 상태 훅. */
export function useExploreFilters(): UseExploreFiltersReturn {
  const [search, setSearch] = useSearchParams();
  const filters = useMemo(() => readFiltersFromSearch(search), [search]);

  const patch = useCallback(
    (delta: Partial<ExploreFilters>) => {
      // 필터(필터 외 page) 변경 시 page=1 리셋. setPage 는 별도.
      const next: ExploreFilters = {
        ...filters,
        ...delta,
        page: 'page' in delta ? (delta.page as number) : 1,
      };
      const sp = writeFiltersToSearch(next);
      setSearch(sp, { replace: false });
    },
    [filters, setSearch],
  );

  const setPage = useCallback(
    (page: number) => {
      const next: ExploreFilters = { ...filters, page };
      setSearch(writeFiltersToSearch(next), { replace: false });
    },
    [filters, setSearch],
  );

  const reset = useCallback(() => {
    setSearch(new URLSearchParams(), { replace: false });
  }, [setSearch]);

  return { filters, patch, setPage, reset };
}

/** Explore API 응답을 React Query 로 구독. slug 없으면 disabled. */
export function useAdongExplore(
  slug: string | null | undefined,
  filters: ExploreFilters,
): UseQueryResult<ExploreResponse> {
  return useQuery({
    queryKey: ['adongs', 'explore', slug, filters],
    queryFn: () => getAdongExplore(slug as string, filters),
    enabled: !!slug,
    staleTime: 30_000,
    placeholderData: (prev) => prev, // 필터 변경 시 깜빡임 줄이기
  });
}
