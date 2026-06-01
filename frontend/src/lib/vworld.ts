import type { ThemeMode } from '@/contexts/ThemeContext';

const VWORLD_KEY = import.meta.env.VITE_VWORLD_API_KEY as string | undefined;

export const VWORLD_ATTRIBUTION = '&copy; <a href="https://www.vworld.kr/">V-World</a> 국토교통부';

export function getVWorldLayer(theme: ThemeMode): 'Base' | 'midnight' {
  return theme === 'dark' ? 'midnight' : 'Base';
}

export function getVWorldTileUrl(theme: ThemeMode): string {
  return `https://api.vworld.kr/req/wmts/1.0.0/${VWORLD_KEY ?? ''}/${getVWorldLayer(theme)}/{z}/{y}/{x}.png`;
}

export const VWORLD_MAX_ZOOM = 18;

export function getVWorldMaxNativeZoom(_theme: ThemeMode): number {
  return VWORLD_MAX_ZOOM;
}

