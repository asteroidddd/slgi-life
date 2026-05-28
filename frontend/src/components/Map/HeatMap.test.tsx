// Phase 4.7 fix 회귀 가드 — GeoJSON feature.properties.adm_cd2 (10자리
// 행정동 코드) 와 AdongScore.code 가 동일 키여야 정상 매칭된다.
//
// Leaflet 컴포넌트 자체 마운트는 jsdom 에서 비용이 높아 실제 렌더 대신
// 매칭 로직만 단위 테스트. (HeatMap 의 styleFn 가 dongByCode[feature.adm_cd2]
// 로 lookup → 같은 키 합의가 핵심.)

import { describe, expect, it } from 'vitest';

import { indexAdongsByCode, pickScore } from './HeatMap';
import type { AdongScore } from '@/types/api';

const SAMPLE: AdongScore[] = [
  {
    slug: 'mapo-seogyo',
    code: '1144055000', // 10자리 — adm_cd2 와 동일 폭
    name: '서교동',
    gu: '마포구',
    score: 78.4,
    lat: 37.55,
    lng: 126.91,
    score_rent: 70,
    score_amenity: 90,
    score_transit: 75,
    score_safety: 80,
  },
  {
    slug: 'jongno-jongno1',
    code: '1111053000',
    name: '종로1.2.3.4가동',
    gu: '종로구',
    score: 60.2,
    lat: 37.57,
    lng: 126.99,
    score_rent: 55,
    score_amenity: 65,
    score_transit: 60,
    score_safety: 50,
  },
];

describe('indexAdongsByCode (HeatMap regression: adm_cd2 ↔ code)', () => {
  it('indexes by 10-자리 code (matches GeoJSON feature.properties.adm_cd2)', () => {
    const idx = indexAdongsByCode(SAMPLE);
    // adm_cd2 와 같은 키로 lookup 가능해야 함.
    expect(idx['1144055000']?.name).toBe('서교동');
    expect(idx['1111053000']?.gu).toBe('종로구');
  });

  it('does NOT index by slug (회귀 — slug 키였던 구버전 패턴 금지)', () => {
    const idx = indexAdongsByCode(SAMPLE);
    expect(idx['mapo-seogyo']).toBeUndefined();
  });
});

describe('pickScore', () => {
  it('returns the right axis for each layer', () => {
    const d = SAMPLE[0];
    expect(pickScore(d, 'composite')).toBe(78.4);
    expect(pickScore(d, 'rent')).toBe(70);
    expect(pickScore(d, 'amenity')).toBe(90);
    expect(pickScore(d, 'transit')).toBe(75);
    expect(pickScore(d, 'safety')).toBe(80);
  });
});
