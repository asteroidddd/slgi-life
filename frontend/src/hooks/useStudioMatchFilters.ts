// Studio Match — 메인 지도 자취 거래량 분포 필터의 URL state hook.
//
// useExploreFilters 와 동일 패턴 (Phase 4.8). 차이점:
//   - sort/page 등 페이지네이션 키 없음 (BaseRentFilters 만)
//   - default 가 자취 평균값으로 좁혀져 있음 (eng-review #1·#2)
//   - setSearch({ replace: true }) — slider drag 중 history 폭주 방지 (#11)
//
// 메인 지도 (`/`) 의 URL 쿼리스트링과 1:1 동기화. 새로고침/공유 안전. Explore
// 페이지로 navigate 시에도 같은 키로 그대로 전달 (#16, BaseRentFilters 공유).

import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

import type { ExploreDealType, ExplorePeriod, MatchFilters } from '@/types/api';

const ALL_DEAL_TYPES: ExploreDealType[] = ['villa', 'dagagu', 'danok', 'officetel', 'apt'];
const PERIOD_VALUES: ExplorePeriod[] = ['3m', '6m', '12m', '24m', 'all'];

/** 첫 진입 default — 자취 평균값으로 좁힘 (eng-review #1).
 *
 * - 거래유형: villa·dagagu·officetel — 단독은 1:1 통째 임대 형태가 아니라 자취
 *   탐색에 노이즈. apt 는 아예 다른 시장.
 * - 기간: 6개월 — 너무 옛 데이터 X, 너무 짧은 표본 X.
 * - 보증금 0~5,000만원 / 월세 30~80만원 / 면적 15~40m² — 자취 시장 90 percentile.
 */
export const DEFAULT_STUDIO_MATCH_FILTERS: MatchFilters = {
  deal_types: ['villa', 'dagagu', 'officetel'],
  period: '6m',
  deposit_min: 0,
  deposit_max: 5_000,
  monthly_min: 30,
  monthly_max: 80,
  converted_min: 0,
  converted_max: 300,
  area_min: 15,
  area_max: 40,
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
  if (!raw) return DEFAULT_STUDIO_MATCH_FILTERS.deal_types;
  const items = raw
    .split(',')
    .map((s) => s.trim())
    .filter((s): s is ExploreDealType => (ALL_DEAL_TYPES as string[]).includes(s));
  return items.length > 0 ? items : DEFAULT_STUDIO_MATCH_FILTERS.deal_types;
}

/** URL 쿼리스트링 → MatchFilters. 검증 실패는 default 로 폴백. */
export function readMatchFiltersFromSearch(search: URLSearchParams): MatchFilters {
  const d = DEFAULT_STUDIO_MATCH_FILTERS;
  return {
    deal_types: parseDealTypes(search.get('deal_types')),
    period: parseEnum<ExplorePeriod>(search.get('period'), PERIOD_VALUES, d.period),
    deposit_min: parseInt32(search.get('deposit_min'), d.deposit_min),
    deposit_max: parseInt32(search.get('deposit_max'), d.deposit_max),
    monthly_min: parseInt32(search.get('monthly_min'), d.monthly_min),
    monthly_max: parseInt32(search.get('monthly_max'), d.monthly_max),
    converted_min: parseInt32(search.get('converted_min'), d.converted_min),
    converted_max: parseInt32(search.get('converted_max'), d.converted_max),
    area_min: parseInt32(search.get('area_min'), d.area_min),
    area_max: parseInt32(search.get('area_max'), d.area_max),
  };
}

/** MatchFilters → URLSearchParams (default 와 같은 값은 omit). */
export function writeMatchFiltersToSearch(
  f: MatchFilters,
  base?: URLSearchParams,
): URLSearchParams {
  const sp = new URLSearchParams(base ?? undefined);
  // 기존 match-related 키 정리 후 다시 쓰기.
  for (const k of [
    'deal_types',
    'period',
    'deposit_min',
    'deposit_max',
    'monthly_min',
    'monthly_max',
    'converted_min',
    'converted_max',
    'area_min',
    'area_max',
  ] as const) {
    sp.delete(k);
  }
  const d = DEFAULT_STUDIO_MATCH_FILTERS;
  if (f.deal_types.join(',') !== d.deal_types.join(',')) {
    sp.set('deal_types', f.deal_types.join(','));
  }
  if (f.period !== d.period) sp.set('period', f.period);
  if (f.deposit_min !== d.deposit_min) sp.set('deposit_min', String(f.deposit_min));
  if (f.deposit_max !== d.deposit_max) sp.set('deposit_max', String(f.deposit_max));
  if (f.monthly_min !== d.monthly_min) sp.set('monthly_min', String(f.monthly_min));
  if (f.monthly_max !== d.monthly_max) sp.set('monthly_max', String(f.monthly_max));
  if (f.converted_min !== d.converted_min) sp.set('converted_min', String(f.converted_min));
  if (f.converted_max !== d.converted_max) sp.set('converted_max', String(f.converted_max));
  if (f.area_min !== d.area_min) sp.set('area_min', String(f.area_min));
  if (f.area_max !== d.area_max) sp.set('area_max', String(f.area_max));
  return sp;
}

/** default 와 동일하면 false (= 초기화 버튼 비표시). */
export function isStudioMatchDirty(f: MatchFilters): boolean {
  const d = DEFAULT_STUDIO_MATCH_FILTERS;
  return (
    f.deal_types.join(',') !== d.deal_types.join(',') ||
    f.period !== d.period ||
    f.deposit_min !== d.deposit_min ||
    f.deposit_max !== d.deposit_max ||
    f.monthly_min !== d.monthly_min ||
    f.monthly_max !== d.monthly_max ||
    f.converted_min !== d.converted_min ||
    f.converted_max !== d.converted_max ||
    f.area_min !== d.area_min ||
    f.area_max !== d.area_max
  );
}

export interface UseStudioMatchFiltersReturn {
  filters: MatchFilters;
  /** 부분 갱신. 다른 필드는 유지. URL replace (drag 중 history 폭주 방지). */
  patch: (delta: Partial<MatchFilters>) => void;
  /** 모든 필터 default 로 리셋. */
  reset: () => void;
}

/** URL 쿼리스트링과 동기화된 Studio Match 필터 상태 훅.
 *
 * @returns filters / patch / reset. patch 는 replace: true 로 history 갱신.
 */
export function useStudioMatchFilters(): UseStudioMatchFiltersReturn {
  const [search, setSearch] = useSearchParams();
  const filters = useMemo(() => readMatchFiltersFromSearch(search), [search]);

  const patch = useCallback(
    (delta: Partial<MatchFilters>) => {
      const next: MatchFilters = { ...filters, ...delta };
      const sp = writeMatchFiltersToSearch(next, search);
      // replace=true: slider drag 중 history pollution 방지 (eng-review #11).
      setSearch(sp, { replace: true });
    },
    [filters, search, setSearch],
  );

  const reset = useCallback(() => {
    const sp = new URLSearchParams(search);
    for (const k of [
      'deal_types',
      'period',
      'deposit_min',
      'deposit_max',
      'monthly_min',
      'monthly_max',
      'converted_min',
      'converted_max',
      'area_min',
      'area_max',
    ] as const) {
      sp.delete(k);
    }
    setSearch(sp, { replace: true });
  }, [search, setSearch]);

  return { filters, patch, reset };
}
