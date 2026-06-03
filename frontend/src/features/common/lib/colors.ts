/**
 * Color helpers — for use OUTSIDE of CSS where token variables are not
 * available. Leaflet (`fillColor`, `color`) and Recharts (`fill`, `stroke`)
 * cannot consume `var(--token)` strings, so this module mirrors the relevant
 * tokens.css values as JS hex constants.
 *
 * Where to use:
 *   - Leaflet polygon fill / stroke colors
 *   - Recharts fill / stroke / grid props
 *   - Any imperative canvas / WebGL drawing
 *
 * Where NOT to use:
 *   - JSX `style={{ color: ... }}` — prefer `var(--color-*)` from tokens.css.
 *
 * Update policy:
 *   These hex values MUST stay in sync with `frontend/src/styles/tokens.css`.
 *   Specifically the `--heatmap-1..5`, `--color-secondary`, `--color-accent`,
 *   `--color-secondary-dark`, `--color-link`, `--color-text`,
 *   `--color-text-muted`, `--color-text-subtle`, `--color-divider` tokens.
 *   If the design system shifts, update both places.
 */

/* -------------------------------------------------------------------------- */
/* Heatmap: 5-stop, Pale Green Wash → Deep Forest                             */
/* -------------------------------------------------------------------------- */

/**
 * 5-stop polygon fill palette, Pale Green Wash → Deep Forest.
 * Mirrors `--heatmap-1` … `--heatmap-5` in tokens.css.
 *
 * Bucket boundaries (per DESIGN_SYSTEM.md):
 *   bucket-1: [ 0, 20)  → #edfce9
 *   bucket-2: [20, 40)  → #b9dfb6
 *   bucket-3: [40, 60)  → #6fa985
 *   bucket-4: [60, 80)  → #2c7559
 *   bucket-5: [80, 100] → #003c33
 */
export const HEATMAP_COLORS = {
  q1: '#edfce9', // 0–20  (Pale Green Wash)
  q2: '#b9dfb6', // 20–40
  q3: '#6fa985', // 40–60
  q4: '#2c7559', // 60–80
  q5: '#003c33', // 80–100 (Deep Forest)
} as const;

/** 5-stop ordered tuple — convenient for legends or `.at(idx)` access. */
export const HEATMAP_COLORS_ORDERED = [
  HEATMAP_COLORS.q1,
  HEATMAP_COLORS.q2,
  HEATMAP_COLORS.q3,
  HEATMAP_COLORS.q4,
  HEATMAP_COLORS.q5,
] as const;

/** Polygon fill for adongs that have no score (data not yet available).
 *  Surface-Alt keeps it on-palette and clearly distinct from the green ramp. */
export const HEATMAP_NO_DATA = '#F4F4F5'; // --color-surface-alt

export type HeatmapBucket = 'q1' | 'q2' | 'q3' | 'q4' | 'q5';

/**
 * Bucket a 0–100 score into one of five quintile buckets.
 * Boundaries: [0,20) / [20,40) / [40,60) / [60,80) / [80,100].
 *
 * Direction note: this function does NOT decide whether "low score = good" or
 * "high score = good". It just maps a number to a bucket. The caller (heatmap
 * layer, score bar) decides what the gradient direction means for each metric.
 */
export function scoreToHeatmapBucket(score: number): HeatmapBucket {
  const s = clamp(score, 0, 100);
  if (s < 20) return 'q1';
  if (s < 40) return 'q2';
  if (s < 60) return 'q3';
  if (s < 80) return 'q4';
  return 'q5';
}

/**
 * 0–100 score → hex color string.
 *
 * The optional second argument is kept for backward call-site compatibility
 * (a few HeatMap.tsx / HeroSection.tsx callers pass `'light'`). The new
 * design system has no dark mode, so the parameter is ignored.
 */
export function scoreToHeatmapColor(
  score: number,
  _theme: 'light' | 'dark' = 'light',
): string {
  return HEATMAP_COLORS[scoreToHeatmapBucket(score)];
}

/* -------------------------------------------------------------------------- */
/* Map polygon stroke (per DESIGN_SYSTEM.md "Map-Specific Shapes")            */
/* -------------------------------------------------------------------------- */

/**
 * Polygon stroke colors for Leaflet.
 *
 * Spec:
 *   - Default adong polygon stroke: 1px #ffffff @ 60% opacity
 *   - Selected polygon stroke:     2px #4C4C4C (Secondary)
 *
 * Leaflet's `style` callback expects `color` (hex) + `opacity` (0..1)
 * separately, so we expose both. There is no separate "dark theme" stroke;
 * the system is light-only.
 */
export const MAP_POLYGON_STROKE = {
  /** Default outline. Apply with `{ color, opacity }`. */
  default: { color: '#ffffff', opacity: 0.6, weight: 1 },
  /** Hover outline — slightly more opaque white, same color. */
  hover: { color: '#ffffff', opacity: 0.85, weight: 1.2 },
  /** Selected outline — Secondary, full opacity. */
  selected: { color: '#4C4C4C', opacity: 1, weight: 2 },

  /** Convenience aliases retained for older callers (HeroSection). */
  light: '#ffffff',
  dark: '#4C4C4C',
} as const;

/**
 * Transaction pin / POI marker colors. Per DESIGN_SYSTEM.md:
 *   - default: Secondary `#4C4C4C`, 12px circle, white inner dot
 *   - selected: Accent `#ff7759`, 16px on hover
 */
export const MAP_PIN = {
  default: '#4C4C4C',
  selected: '#ff7759',
  innerDot: '#ffffff',
} as const;

/* -------------------------------------------------------------------------- */
/* Recharts palette                                                           */
/* -------------------------------------------------------------------------- */

/**
 * Recharts color palette — for the adong detail page (SPEC 6.3) and any
 * other charts. Chart shell stays mono (--color-text + axis --color-divider
 * + grid --color-divider); colored series are reserved for "data is the
 * hero" moments.
 *
 * The three rent-trend lines use the **mono text + Link + Accent**
 * triplet so all three are readable on the same axes without resurrecting
 * the previous 4-color category palette. If a future chart needs a 5-step
 * sequential palette, use `HEATMAP_COLORS_ORDERED`.
 *
 * Mapping (SPEC 6.3 RealEstate trend chart, 4 series):
 *   villa     → Text (#212121)        — primary series, monochrome
 *   dagagu    → Link (#1863dc)       — secondary line (옛 multi 자리 이어받음)
 *   danok     → Slate Mid (#6b7280)  — tertiary, 단독 = mature mid-grey
 *   officetel → Accent (#ff7759)     — warm accent
 *
 * Phase 1 RDS 통합으로 단독다가구(multi) 카테고리가 다가구(dagagu)·단독(danok)
 * 두 시리즈로 분리됨. 차트 라인 4개로 늘어남 (apt는 별도 시장이라 미포함).
 */
export const CHART_COLORS = {
  /** 연립다세대 (villa) — primary series, Text. */
  villa: '#212121',
  /** 다가구 (dagagu) — Link. 자취 시장의 본진. */
  dagagu: '#1863dc',
  /** 단독 (danok) — Slate Mid. */
  danok: '#6b7280',
  /** 단독다가구 (danok_dagagu) — neutral bridge for unresolved source rows. */
  danok_dagagu: '#4b5563',
  /** 오피스텔 (officetel) — Accent. */
  officetel: '#ff7759',
  /** 아파트 (apt) — Purple. 자취 4종과 구별되는 보라 계열. */
  apt: '#8b5cf6',
  /** Generic bar fill — Primary green for deposit bands. */
  bar: '#059669',
  /** Axis tick / label color — Text Muted. */
  axis: '#75758a',
  /** Recharts grid line color — Divider. */
  grid: '#d9d9dd',
  /**
   * Warning swatch — mirrors `--color-warning`. For chart series that carry a
   * mild "주의" signal (not bad enough for danger red).
   */
  warning: '#FFD82A',
  /**
   * Deeper warning swatch — mirrors `--color-warning-deep`. For chart series
   * that need more contrast than the pale `warning` yellow (e.g. 음주운전·뺑소니
   * 비율 막대). Sits between warning and danger in semantic weight.
   */
  warningDeep: '#F59E0B',
} as const;

/* -------------------------------------------------------------------------- */
/* Category colors — dashboard section headers / icons                         */
/* -------------------------------------------------------------------------- */

export const CATEGORY_COLORS = {
  realestate: '#F59E0B',
  transport:  '#3B82F6',
  amenity:    '#10B981',
  safety:     '#EF4444',
  population: '#8B5CF6',
  environment:'#14B8A6',
} as const;

export type CategoryKey = keyof typeof CATEGORY_COLORS;

/* -------------------------------------------------------------------------- */
/* Heatmap layer colors — per-layer 5-stop palettes (SPEC 4.6)                */
/* -------------------------------------------------------------------------- */

export type HeatmapLayerKey = 'composite' | 'rent' | 'activity' | 'youth' | 'studio' | 'safety';

export const HEATMAP_LAYER_COLORS: Record<HeatmapLayerKey, readonly [string, string, string, string, string]> = {
  composite: ['#edfce9', '#b9dfb6', '#6fa985', '#2c7559', '#003c33'],
  rent:      ['#FEF3C7', '#FDE68A', '#FBBF24', '#F59E0B', '#D97706'],
  activity:  ['#FCE7F3', '#F9A8D4', '#EC4899', '#BE185D', '#831843'],
  youth:     ['#EDE9FE', '#C4B5FD', '#8B5CF6', '#6D28D9', '#4C1D95'],
  studio:    ['#CCFBF1', '#99F6E4', '#2DD4BF', '#0D9488', '#115E59'],
  safety:    ['#EF4444', '#FB923C', '#FBBF24', '#84CC16', '#22C55E'],
} as const;

/**
 * Map a 0-100 score to the appropriate color for a given heatmap layer.
 * Uses the same quintile bucket boundaries as scoreToHeatmapBucket.
 */
export function scoreToLayerColor(score: number, layer: HeatmapLayerKey): string {
  const s = clamp(score, 0, 100);
  const colors = HEATMAP_LAYER_COLORS[layer];
  if (s < 20) return colors[0];
  if (s < 40) return colors[1];
  if (s < 60) return colors[2];
  if (s < 80) return colors[3];
  return colors[4];
}

/* -------------------------------------------------------------------------- */
/* Internal                                                                   */
/* -------------------------------------------------------------------------- */

function clamp(v: number, min: number, max: number): number {
  if (Number.isNaN(v)) return min;
  return Math.max(min, Math.min(max, v));
}
