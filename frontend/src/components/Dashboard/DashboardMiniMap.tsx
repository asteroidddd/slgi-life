// DashboardMiniMap -- SPEC 4.3 mini map for the dashboard (1/4 of outlet).
//
// Separate from components/Map/HeatMap.tsx (which is frozen for MainMap).
// Reuses the same data hooks and color utilities.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import type { Feature, Geometry, Polygon } from 'geojson';
import type { LatLngBounds, Layer, LeafletMouseEvent } from 'leaflet';
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet';
import { useNavigate } from 'react-router-dom';

import { useTheme } from '@/contexts/ThemeContext';
import { useAdongGeoJson, useLdongGeoJson } from '@/hooks/useAdongGeoJson';
import type { AdongFeatureProps } from '@/hooks/useAdongGeoJson';
import { MAP_POLYGON_STROKE } from '@/lib/colors';
import { VWORLD_ATTRIBUTION, getVWorldMaxNativeZoom, getVWorldTileUrl } from '@/lib/vworld';
import type { AdongScore } from '@/types/api';

import 'leaflet/dist/leaflet.css';

const SEOUL_CENTER: [number, number] = [37.5665, 126.978];
const MINI_ZOOM = 13;

type DongFeature = Feature<Geometry, AdongFeatureProps>;
type RegionMaskFeature = Feature<Polygon, { name: string }>;

const REGION_MASK_OUTER_RING = [
  [124.0, 33.0],
  [130.5, 33.0],
  [130.5, 39.5],
  [124.0, 39.5],
  [124.0, 33.0],
];

const REGION_MASK_STYLE = {
  color: 'transparent',
  weight: 0,
  opacity: 0,
  fillColor: '#6b7280',
  fillOpacity: 0.45,
  fillRule: 'evenodd' as const,
  className: 'map-seoul-mask',
};

function selectedRings(feature?: DongFeature | null): number[][][] {
  if (!feature) return [];
  const geometry = feature.geometry;
  if (geometry.type === 'Polygon') return [geometry.coordinates[0]];
  if (geometry.type === 'MultiPolygon') {
    return geometry.coordinates.reduce<number[][][]>((acc, polygon) => {
      if (polygon[0]) acc.push(polygon[0]);
      return acc;
    }, []);
  }
  return [];
}

function featureCode(feature?: DongFeature | null): string {
  const p = feature?.properties as (AdongFeatureProps & {
    adong_code?: string;
    ldong_code?: string;
    code?: string;
    slug?: string;
  }) | undefined;
  return p?.adm_cd2 ?? p?.adm_cd ?? p?.adong_code ?? p?.ldong_code ?? p?.code ?? p?.slug ?? '';
}

function featureName(feature?: DongFeature | null): string {
  const p = feature?.properties as (AdongFeatureProps & { name?: string }) | undefined;
  return p?.adm_nm ?? p?.name ?? '';
}

function regionMaskFeatureFor(feature?: DongFeature | null): RegionMaskFeature | null {
  const holes = selectedRings(feature);
  if (!holes.length) return null;
  return {
    type: 'Feature',
    properties: { name: '선택 동 외부 마스크' },
    geometry: {
      type: 'Polygon',
      coordinates: [REGION_MASK_OUTER_RING, ...holes],
    },
  };
}

interface DashboardMiniMapProps {
  regions: AdongScore[];
  regionLevel: 'adong' | 'ldong';
  selectedSlug: string | null;
  onRegionSelect: (slug: string) => void;
}

export default function DashboardMiniMap({
  regions,
  regionLevel,
  selectedSlug,
  onRegionSelect,
}: DashboardMiniMapProps) {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const [expanding, setExpanding] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const adongGeo = useAdongGeoJson();
  const ldongGeo = useLdongGeoJson();
  const geojson = regionLevel === 'ldong' ? ldongGeo.data : adongGeo.data;
  const geoLoading = regionLevel === 'ldong' ? ldongGeo.isLoading : adongGeo.isLoading;

  const dongByCode = useMemo(() => {
    const m: Record<string, AdongScore> = {};
    for (const d of regions) m[d.code] = d;
    return m;
  }, [regions]);

  const selectedRegion = useMemo(
    () => regions.find((d) => d.slug === selectedSlug) ?? null,
    [regions, selectedSlug],
  );

  const center: [number, number] = selectedRegion
    ? [selectedRegion.lat, selectedRegion.lng]
    : SEOUL_CENTER;

  const selectedFeature = useMemo<DongFeature | null>(() => {
    const features = geojson && 'features' in geojson ? geojson.features : [];
    return (features.find((feature) => {
      const typed = feature as DongFeature;
      const code = featureCode(typed);
      const name = featureName(typed);
      return code === selectedRegion?.code || code === selectedSlug || name === selectedRegion?.name;
    }) as DongFeature | undefined) ?? null;
  }, [geojson, selectedRegion?.code, selectedRegion?.name, selectedSlug]);

  const selectedBounds = useMemo<LatLngBounds | null>(() => {
    if (!selectedFeature) return null;
    const bounds = L.geoJSON(selectedFeature).getBounds();
    return bounds.isValid() ? bounds : null;
  }, [selectedFeature]);

  const selectedMask = useMemo(() => regionMaskFeatureFor(selectedFeature), [selectedFeature]);
  const selectedMaskKey = useMemo(
    () => `mini-mask-${regionLevel}-${selectedSlug ?? 'none'}-${featureCode(selectedFeature) || 'none'}`,
    [regionLevel, selectedFeature, selectedSlug],
  );

  const layerKey = useMemo(
    () => `mini-outline-${regionLevel}-${regions.length}-${selectedSlug ?? ''}`,
    [regionLevel, regions.length, selectedSlug],
  );

  const styleFn = useCallback(
    (feature?: Feature<Geometry, AdongFeatureProps>) => {
      const code = featureCode(feature as DongFeature);
      const region = dongByCode[code];
      const isSelected = region?.slug === selectedSlug;

      return {
        color: isSelected ? MAP_POLYGON_STROKE.selected.color : 'transparent',
        weight: isSelected ? 2 : 0,
        opacity: isSelected ? 1 : 0,
        fillColor: isSelected ? 'var(--color-heatmap-2)' : 'transparent',
        fillOpacity: isSelected ? 0.12 : 0,
      };
    },
    [dongByCode, selectedSlug],
  );

  const onEachFeature = useCallback(
    (feature: Feature<Geometry, AdongFeatureProps>, layer: Layer) => {
      const code = featureCode(feature as DongFeature);
      const region = dongByCode[code];
      if (!region) return;

      layer.bindTooltip(
        `<div class="map-tooltip__name">${region.gu} ${region.name}</div>` +
          `<div class="map-tooltip__score tabular">종합 ${region.score.toFixed(1)}</div>`,
        { sticky: true, direction: 'top', offset: [0, -4], opacity: 1 },
      );

      layer.on({
        click: (e: LeafletMouseEvent) => {
          L.DomEvent.stopPropagation(e);
          onRegionSelect(region.slug);
        },
        mouseover: (e) => {
          if (region.slug === selectedSlug) {
            (e.target as { setStyle: (s: object) => void }).setStyle({ fillOpacity: 0.18, weight: 2.5 });
          }
        },
        mouseout: (e) => {
          if (region.slug === selectedSlug) {
            (e.target as { setStyle: (s: object) => void }).setStyle({ fillOpacity: 0.12, weight: 2 });
          }
        },
      });
    },
    [dongByCode, onRegionSelect, selectedSlug],
  );

  const handleExpand = useCallback(() => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      document.documentElement.style.setProperty('--map-transition-left', `${rect.left}px`);
      document.documentElement.style.setProperty('--map-transition-top', `${rect.top}px`);
      document.documentElement.style.setProperty('--map-transition-width', `${rect.width}px`);
      document.documentElement.style.setProperty('--map-transition-height', `${rect.height}px`);
    }
    setExpanding(true);
    window.setTimeout(() => {
      navigate(selectedSlug && regionLevel === 'adong' ? `/?mode=heatmap&adong=${selectedSlug}` : '/?mode=heatmap');
    }, 360);
  }, [navigate, regionLevel, selectedSlug]);

  if (geoLoading || !geojson) {
    return (
      <div className="w-full h-full min-h-[300px] bg-surface-alt rounded-[var(--radius-sm)] border border-border flex items-center justify-center">
        <span className="text-caption text-text-muted">지도 불러오는 중...</span>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full h-full min-h-[300px] rounded-[var(--radius-sm)] overflow-hidden border border-border">
      <MapContainer
        center={center}
        zoom={MINI_ZOOM}
        zoomSnap={0}
        zoomDelta={0.25}
        zoomControl={false}
        scrollWheelZoom={true}
        dragging={true}
        attributionControl={false}
        style={{ width: '100%', height: '100%', minHeight: 300 }}
      >
        <TileLayer
          url={getVWorldTileUrl(theme)}
          attribution={VWORLD_ATTRIBUTION}
          maxNativeZoom={getVWorldMaxNativeZoom(theme)}
        />
        <MiniMapViewport center={center} zoom={MINI_ZOOM} bounds={selectedBounds} />
        {selectedMask ? <GeoJSON key={selectedMaskKey} data={selectedMask} style={REGION_MASK_STYLE} interactive={false} /> : null}
        <GeoJSON
          key={layerKey}
          data={geojson}
          style={styleFn}
          onEachFeature={onEachFeature}
        />
      </MapContainer>

      {/* Expand button */}
      <button
        type="button"
        onClick={handleExpand}
        className="absolute top-3 right-3 z-[1000] w-8 h-8 rounded-[var(--radius-sm)] bg-surface/90 border border-border flex items-center justify-center text-text-muted hover:text-text hover:bg-surface cursor-pointer transition-colors"
        aria-label="맵뷰에서 보기"
        title="맵뷰에서 보기"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M1 5V1h4M9 1h4v4M13 9v4H9M5 13H1V9" />
        </svg>
      </button>

      {expanding ? (
        <div className="map-route-transition map-route-transition--in" aria-hidden="true">
          <div className="map-route-transition__frame" />
        </div>
      ) : null}

    </div>
  );
}

function MiniMapViewport({ center, zoom, bounds }: { center: [number, number]; zoom: number; bounds: LatLngBounds | null }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) {
      const size = map.getSize();
      const boundsCenter = bounds.getCenter();
      const crs = map.options.crs ?? L.CRS.EPSG3857;
      const north = crs.latLngToPoint(L.latLng(bounds.getNorth(), boundsCenter.lng), 0);
      const south = crs.latLngToPoint(L.latLng(bounds.getSouth(), boundsCenter.lng), 0);
      const yDistance = Math.abs(south.y - north.y);
      if (size.y > 0 && yDistance > 0) {
        const verticalZoom = Math.min(20, Math.log2(size.y / yDistance));
        map.setView(boundsCenter, verticalZoom, { animate: true });
      } else {
        map.fitBounds(bounds, { animate: true, padding: [0, 0], maxZoom: 20 });
      }
      return;
    }
    map.setView(center, zoom, { animate: true });
  }, [bounds, center, map, zoom]);
  return null;
}
