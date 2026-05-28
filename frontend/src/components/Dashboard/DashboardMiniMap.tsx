// DashboardMiniMap -- SPEC 4.3 mini map for the dashboard (1/4 of outlet).
//
// Separate from components/Map/HeatMap.tsx (which is frozen for MainMap).
// Reuses the same data hooks and color utilities.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import type { Feature, Geometry } from 'geojson';
import type { Layer, LeafletMouseEvent } from 'leaflet';
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet';
import { useNavigate } from 'react-router-dom';

import { useAdongGeoJson } from '@/hooks/useAdongGeoJson';
import type { AdongFeatureProps } from '@/hooks/useAdongGeoJson';
import { MAP_POLYGON_STROKE } from '@/lib/colors';
import type { AdongScore } from '@/types/api';

import 'leaflet/dist/leaflet.css';

const SEOUL_CENTER: [number, number] = [37.5665, 126.978];
const MINI_ZOOM = 15;

const VWORLD_KEY = import.meta.env.VITE_VWORLD_API_KEY as string | undefined;
const TILE_URL = `https://api.vworld.kr/req/wmts/1.0.0/${VWORLD_KEY ?? ''}/Base/{z}/{y}/{x}.png`;
const TILE_ATTR = '&copy; <a href="https://www.vworld.kr/">V-World</a>';

interface DashboardMiniMapProps {
  adongs: AdongScore[];
  selectedSlug: string | null;
  onAdongSelect: (slug: string) => void;
}

export default function DashboardMiniMap({
  adongs,
  selectedSlug,
  onAdongSelect,
}: DashboardMiniMapProps) {
  const navigate = useNavigate();
  const [expanding, setExpanding] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { data: geojson, isLoading: geoLoading } = useAdongGeoJson();

  const dongByCode = useMemo(() => {
    const m: Record<string, AdongScore> = {};
    for (const d of adongs) m[d.code] = d;
    return m;
  }, [adongs]);

  const selectedAdong = useMemo(
    () => adongs.find((d) => d.slug === selectedSlug) ?? null,
    [adongs, selectedSlug],
  );

  const center: [number, number] = selectedAdong
    ? [selectedAdong.lat, selectedAdong.lng]
    : SEOUL_CENTER;

  const layerKey = useMemo(() => `mini-outline-${adongs.length}-${selectedSlug ?? ''}`, [adongs.length, selectedSlug]);

  const styleFn = useCallback(
    (feature?: Feature<Geometry, AdongFeatureProps>) => {
      const code = feature?.properties?.adm_cd2 ?? '';
      const adong = dongByCode[code];
      const isSelected = adong?.slug === selectedSlug;

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
      const code = feature.properties.adm_cd2 ?? '';
      const adong = dongByCode[code];
      if (!adong) return;

      layer.bindTooltip(
        `<div class="map-tooltip__name">${adong.gu} ${adong.name}</div>` +
          `<div class="map-tooltip__score tabular">종합 ${adong.score.toFixed(1)}</div>`,
        { sticky: true, direction: 'top', offset: [0, -4], opacity: 1 },
      );

      layer.on({
        click: (e: LeafletMouseEvent) => {
          L.DomEvent.stopPropagation(e);
          onAdongSelect(adong.slug);
        },
        mouseover: (e) => {
          if (adong.slug === selectedSlug) {
            (e.target as { setStyle: (s: object) => void }).setStyle({ fillOpacity: 0.18, weight: 2.5 });
          }
        },
        mouseout: (e) => {
          if (adong.slug === selectedSlug) {
            (e.target as { setStyle: (s: object) => void }).setStyle({ fillOpacity: 0.12, weight: 2 });
          }
        },
      });
    },
    [dongByCode, onAdongSelect, selectedSlug],
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
      navigate(selectedSlug ? `/?mode=heatmap&adong=${selectedSlug}` : '/?mode=heatmap');
    }, 360);
  }, [navigate, selectedSlug]);

  if (geoLoading || !geojson) {
    return (
      <div className="w-full h-full min-h-[300px] bg-surface-alt rounded-card border border-border flex items-center justify-center">
        <span className="text-caption text-text-muted">지도 불러오는 중...</span>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full h-full min-h-[300px] rounded-card overflow-hidden border border-border">
      <MapContainer
        center={center}
        zoom={MINI_ZOOM}
        zoomControl={false}
        scrollWheelZoom={true}
        dragging={true}
        attributionControl={false}
        style={{ width: '100%', height: '100%', minHeight: 300 }}
      >
        <TileLayer url={TILE_URL} attribution={TILE_ATTR} />
        <MiniMapViewport center={center} zoom={MINI_ZOOM} />
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
        className="absolute top-3 right-3 z-[1000] w-8 h-8 rounded-md bg-surface/90 border border-border flex items-center justify-center text-text-muted hover:text-text hover:bg-surface cursor-pointer transition-colors"
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

function MiniMapViewport({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom, { animate: true });
  }, [center, map, zoom]);
  return null;
}
