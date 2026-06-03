// Smoke test for scoreToHeatmapBucket — 5분위 boundary 회귀 가드.
//
// 5단 그린 그라데이션은 DESIGN_SYSTEM.md 의 단일 진실. 경계값(0/19/20/40/60/80/100)
// 이 잘못 분기되면 히트맵 색이 즉시 어긋나므로 테스트로 잠가둔다.

import { describe, expect, it } from 'vitest';

import { HEATMAP_COLORS, scoreToHeatmapBucket, scoreToHeatmapColor } from './colors';

describe('scoreToHeatmapBucket', () => {
  it('0 → q1', () => {
    expect(scoreToHeatmapBucket(0)).toBe('q1');
  });
  it('19.99 → q1 (upper-open boundary)', () => {
    expect(scoreToHeatmapBucket(19.99)).toBe('q1');
  });
  it('20 → q2 (lower-closed boundary)', () => {
    expect(scoreToHeatmapBucket(20)).toBe('q2');
  });
  it('40 → q3', () => {
    expect(scoreToHeatmapBucket(40)).toBe('q3');
  });
  it('60 → q4', () => {
    expect(scoreToHeatmapBucket(60)).toBe('q4');
  });
  it('80 → q5', () => {
    expect(scoreToHeatmapBucket(80)).toBe('q5');
  });
  it('100 → q5 (upper-closed boundary)', () => {
    expect(scoreToHeatmapBucket(100)).toBe('q5');
  });
});

describe('scoreToHeatmapColor', () => {
  it('returns the exact 5-stop hex from HEATMAP_COLORS', () => {
    expect(scoreToHeatmapColor(0)).toBe(HEATMAP_COLORS.q1);
    expect(scoreToHeatmapColor(50)).toBe(HEATMAP_COLORS.q3);
    expect(scoreToHeatmapColor(100)).toBe(HEATMAP_COLORS.q5);
  });
});
