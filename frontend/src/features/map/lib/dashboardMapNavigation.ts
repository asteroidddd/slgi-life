export type DashboardMapRegionLevel = 'adong' | 'ldong';

export interface DashboardMapView {
  lat: number;
  lng: number;
  zoom: number;
}

export interface DashboardMapTransitionRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface DashboardMapOpenPayload {
  returnTo: string;
  regionLevel: DashboardMapRegionLevel;
  regionSlug: string | null;
  view: DashboardMapView | null;
  rect: DashboardMapTransitionRect | null;
  updatedAt: number;
}

export const DASHBOARD_MAP_OPEN_STORAGE_KEY = 'dashboard.map.openPayload';
export const MAP_RETURN_STORAGE_KEY = 'app.map.returnTo';

const MAX_PAYLOAD_AGE_MS = 10 * 60 * 1000;
const DASHBOARD_MAP_OPEN_ZOOM_OFFSET = 2;

function finiteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function normalizeView(value: unknown): DashboardMapView | null {
  const source = value as Partial<DashboardMapView> | null | undefined;
  if (!source || !finiteNumber(source.lat) || !finiteNumber(source.lng) || !finiteNumber(source.zoom)) {
    return null;
  }
  return {
    lat: source.lat,
    lng: source.lng,
    zoom: Math.max(3, Math.min(19, source.zoom)),
  };
}

function normalizeRect(value: unknown): DashboardMapTransitionRect | null {
  const source = value as Partial<DashboardMapTransitionRect> | null | undefined;
  if (
    !source
    || !finiteNumber(source.left)
    || !finiteNumber(source.top)
    || !finiteNumber(source.width)
    || !finiteNumber(source.height)
    || source.width <= 0
    || source.height <= 0
  ) {
    return null;
  }
  return {
    left: source.left,
    top: source.top,
    width: source.width,
    height: source.height,
  };
}

function isRegionLevel(value: unknown): value is DashboardMapRegionLevel {
  return value === 'adong' || value === 'ldong';
}

export function buildDashboardMapUrl(payload: DashboardMapOpenPayload) {
  const params = new URLSearchParams();
  params.set('region_level', payload.regionLevel);
  params.set('focus', 'dashboard');
  if (payload.regionSlug) params.set('region_slug', payload.regionSlug);

  const view = normalizeView(payload.view);
  if (view) {
    params.set('lat', view.lat.toFixed(6));
    params.set('lng', view.lng.toFixed(6));
    params.set('zoom', Math.min(19, view.zoom + DASHBOARD_MAP_OPEN_ZOOM_OFFSET).toFixed(2));
  }

  return `/map?${params.toString()}`;
}

export function writeDashboardMapOpenPayload(payload: DashboardMapOpenPayload) {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(DASHBOARD_MAP_OPEN_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Storage may be unavailable. Navigation still works with the mini-map button.
  }
}

export function readDashboardMapOpenPayload(): DashboardMapOpenPayload | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(DASHBOARD_MAP_OPEN_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<DashboardMapOpenPayload>;
    if (!isRegionLevel(parsed.regionLevel)) return null;
    const updatedAt = finiteNumber(parsed.updatedAt) ? parsed.updatedAt : 0;
    if (!updatedAt || Date.now() - updatedAt > MAX_PAYLOAD_AGE_MS) return null;

    return {
      returnTo: typeof parsed.returnTo === 'string' ? parsed.returnTo : '',
      regionLevel: parsed.regionLevel,
      regionSlug: typeof parsed.regionSlug === 'string' ? parsed.regionSlug : null,
      view: normalizeView(parsed.view),
      rect: normalizeRect(parsed.rect),
      updatedAt,
    };
  } catch {
    return null;
  }
}

export function applyDashboardMapTransitionRect(rect: DashboardMapTransitionRect | null | undefined) {
  if (typeof document === 'undefined') return;
  const safeRect = normalizeRect(rect);
  if (!safeRect) return;
  document.documentElement.style.setProperty('--map-transition-left', `${safeRect.left}px`);
  document.documentElement.style.setProperty('--map-transition-top', `${safeRect.top}px`);
  document.documentElement.style.setProperty('--map-transition-width', `${safeRect.width}px`);
  document.documentElement.style.setProperty('--map-transition-height', `${safeRect.height}px`);
}
