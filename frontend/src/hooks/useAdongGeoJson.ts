// Fetches the static Seoul 행정동 GeoJSON once and caches via TanStack Query.
// Joined with score data by feature.properties.adm_cd === adong.slug.
//
// 파일 원본은 backend/data/adong_boundaries.geojson 이며 백엔드 API가 정규화해 서빙한다.
// raqoon886/Local_HangJeongAdong 형식 (adm_cd, sggnm, adm_nm 등).

import { useQuery } from '@tanstack/react-query';
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson';

export interface AdongFeatureProps {
  adm_nm: string;
  adm_cd: string;
  adm_cd2?: string;
  sgg?: string;
  sido?: string;
  sidonm?: string;
  sggnm?: string;
}

export type AdongFeatureCollection = FeatureCollection<
  Polygon | MultiPolygon,
  AdongFeatureProps
>;

export const ADONG_GEOJSON_QUERY_KEY = ['api', 'geojson', 'adongs'] as const;

const GEOJSON_URL = '/api/geojson/adongs';

export async function fetchAdongGeoJson(): Promise<AdongFeatureCollection> {
  const res = await fetch(GEOJSON_URL);
  if (!res.ok) {
    throw new Error(`GeoJSON fetch failed: ${res.status}`);
  }
  return (await res.json()) as AdongFeatureCollection;
}

export function useAdongGeoJson() {
  return useQuery({
    queryKey: ADONG_GEOJSON_QUERY_KEY,
    queryFn: fetchAdongGeoJson,
    staleTime: Infinity,           // 정적 파일이라 캐시 무한
    gcTime: Infinity,
    refetchOnWindowFocus: false,
  });
}
