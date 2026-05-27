import { useQuery } from '@tanstack/react-query';
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson';

export type SeoulMaskFeatureCollection = FeatureCollection<
  Polygon | MultiPolygon,
  { name?: string }
>;

export const SEOUL_MASK_GEOJSON_QUERY_KEY = ['api', 'geojson', 'seoul-mask'] as const;

const GEOJSON_URL = '/api/geojson/seoul-mask';

export async function fetchSeoulMaskGeoJson(): Promise<SeoulMaskFeatureCollection> {
  const res = await fetch(GEOJSON_URL);
  if (!res.ok) {
    throw new Error(`Seoul mask GeoJSON fetch failed: ${res.status}`);
  }
  return (await res.json()) as SeoulMaskFeatureCollection;
}

export function useSeoulMaskGeoJson() {
  return useQuery({
    queryKey: SEOUL_MASK_GEOJSON_QUERY_KEY,
    queryFn: fetchSeoulMaskGeoJson,
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnWindowFocus: false,
  });
}
