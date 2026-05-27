// useStudioMatchFilters helper tests — pure URL ↔ filters parsing.
//
// React hook 자체는 router 가 필요해 별도 (테스트 시간 절약). pure 함수만 검증.

import { describe, expect, it } from 'vitest';

import {
  DEFAULT_STUDIO_MATCH_FILTERS,
  isStudioMatchDirty,
  readMatchFiltersFromSearch,
  writeMatchFiltersToSearch,
} from './useStudioMatchFilters';

describe('readMatchFiltersFromSearch', () => {
  it('empty search → default', () => {
    const f = readMatchFiltersFromSearch(new URLSearchParams());
    expect(f).toEqual(DEFAULT_STUDIO_MATCH_FILTERS);
  });

  it('parses deal_types csv', () => {
    const sp = new URLSearchParams('deal_types=villa,officetel');
    const f = readMatchFiltersFromSearch(sp);
    expect(f.deal_types).toEqual(['villa', 'officetel']);
  });

  it('falls back to default on invalid period', () => {
    const sp = new URLSearchParams('period=999');
    const f = readMatchFiltersFromSearch(sp);
    expect(f.period).toBe(DEFAULT_STUDIO_MATCH_FILTERS.period);
  });

  it('parses int ranges', () => {
    const sp = new URLSearchParams('deposit_max=2000&monthly_min=20');
    const f = readMatchFiltersFromSearch(sp);
    expect(f.deposit_max).toBe(2000);
    expect(f.monthly_min).toBe(20);
  });
});

describe('writeMatchFiltersToSearch', () => {
  it('default filters → empty params (omit-when-equal)', () => {
    const sp = writeMatchFiltersToSearch(DEFAULT_STUDIO_MATCH_FILTERS);
    expect(sp.toString()).toBe('');
  });

  it('writes only changed fields', () => {
    const sp = writeMatchFiltersToSearch({
      ...DEFAULT_STUDIO_MATCH_FILTERS,
      monthly_max: 60,
    });
    expect(sp.get('monthly_max')).toBe('60');
    expect(sp.get('period')).toBeNull();
  });

  it('preserves unrelated query keys passed in base', () => {
    const base = new URLSearchParams('foo=bar');
    const sp = writeMatchFiltersToSearch(
      { ...DEFAULT_STUDIO_MATCH_FILTERS, deposit_max: 2000 },
      base,
    );
    expect(sp.get('foo')).toBe('bar');
    expect(sp.get('deposit_max')).toBe('2000');
  });
});

describe('isStudioMatchDirty', () => {
  it('default → not dirty', () => {
    expect(isStudioMatchDirty(DEFAULT_STUDIO_MATCH_FILTERS)).toBe(false);
  });
  it('changed monthly → dirty', () => {
    expect(
      isStudioMatchDirty({ ...DEFAULT_STUDIO_MATCH_FILTERS, monthly_max: 99 }),
    ).toBe(true);
  });
  it('reordered deal_types → dirty (순서 의미 있음)', () => {
    expect(
      isStudioMatchDirty({
        ...DEFAULT_STUDIO_MATCH_FILTERS,
        deal_types: ['officetel', 'villa', 'dagagu'],
      }),
    ).toBe(true);
  });
});
