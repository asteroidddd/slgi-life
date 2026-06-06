// Leaflet 기반 행정동 히트맵 (SPEC 6.1) — VWorld 타일.
//
// 카카오맵 SDK 통합이 폴리곤 렌더링에서 일관성 문제를 일으켜 다시 Leaflet으로
// 복원. 타일은 VWorld(국토교통부)만 사용한다.
//
// /seoul_dongs.geojson 정적 파일에서 425개 행정동 경계를 1회 로드하고
// feature.properties.adm_cd2 (10자리 행정동 코드) === adong.code 로 score 데이터와 조인.
//
// VWorld 키: frontend/.env 의 VITE_VWORLD_API_KEY.
//   - fallback 타일은 쓰지 않는다. 키가 없으면 V-World 요청이 실패하므로 환경값을 먼저 고친다.
//   - 키 발급: https://www.vworld.kr/ (회원가입 → 인증키 신청 → localhost 도메인 등록)

import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import L from 'leaflet';
import type { Layer, LeafletMouseEvent } from 'leaflet';
import type { Feature, Geometry } from 'geojson';
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet';

import { useTheme } from '@/features/common/contexts/ThemeContext';
import { useAdongGeoJson, useLdongGeoJson } from '@/features/map/hooks/useAdongGeoJson';
import { useSeoulMaskGeoJson } from '@/features/map/hooks/useSeoulMaskGeoJson';
import type { AdongFeatureCollection, AdongFeatureProps } from '@/features/map/hooks/useAdongGeoJson';
import { HEATMAP_NO_DATA, MAP_POLYGON_STROKE, scoreToHeatmapColor } from '@/features/common/lib/colors';
import { VWORLD_ATTRIBUTION, getVWorldMaxNativeZoom, getVWorldTileUrl } from '@/features/map/lib/vworld';
import type { AdongScore } from '@/features/common/types/api';

import 'leaflet/dist/leaflet.css';

const SEOUL_CITY_HALL: [number, number] = [37.5665, 126.978];
const INITIAL_ZOOM = 13;


function cssNumberToken(name: string, fallback: number): number {
  if (typeof window === 'undefined') return fallback;
  const value = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function cssColorToken(name: string): string {
  return `var(${name})`;
}

/** 레이어 탭 — 색상의 기준이 되는 점수 축. */
export type ScoreLayerKey = 'composite' | 'rent' | 'amenity' | 'transit' | 'safety';

export interface HeatMapProps {
  /** 히트맵 점수 데이터. */
  adongs: AdongScore[];
  onAdongClick?: (adong: AdongScore) => void;
  /** 히트맵 폴리곤 표시 여부. false면 베이스맵만 보임. */
  heatmapVisible?: boolean;
  /** 색상 기준이 되는 점수 축. 기본 'composite' (가중합). */
  activeLayer?: ScoreLayerKey;
  /** 추가 레이어를 MapContainer 내부에 렌더링. react-leaflet 컴포넌트만 (e.g.,
   *  CircleMarker, useMap 사용 컴포넌트). 일반 DOM 노드는 작동 안 함. */
  children?: ReactNode;
  regionLevel?: 'adong' | 'ldong';
  selectedRegionSlug?: string | null;
  selectedRegionLevel?: 'adong' | 'ldong';
  selectedRegionAdongs?: AdongScore[];
  selectedRegionFocusKey?: string | null;
  initialCenter?: [number, number];
  initialZoom?: number;
}

function isFiniteScore(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export function pickScore(d: AdongScore, layer: ScoreLayerKey): number | null {
  switch (layer) {
    case 'rent':
      return d.score_rent;
    case 'amenity':
      return d.score_amenity;
    case 'transit':
      return d.score_transit;
    case 'safety':
      return d.score_safety;
    case 'composite':
    default:
      return d.score;
  }
}

function isSelectedFeature(
  feature: Feature<Geometry, AdongFeatureProps>,
  dongByCode: Record<string, AdongScore>,
  selectedRegionSlug: string,
) {
  const code = feature.properties?.adm_cd2 ?? '';
  const dong = dongByCode[code];
  return dong?.slug === selectedRegionSlug || dong?.code === selectedRegionSlug || code === selectedRegionSlug;
}

/** Phase 4.7 fix 회귀 가드용 헬퍼. GeoJSON feature.properties.adm_cd2 (10자리
 *  행정동 코드) 와 AdongScore.code 가 동일 키여야 정상 매칭된다. 7자리 adm_cd 로
 *  매칭하던 옛 코드가 RDS 통합 후 깨졌으므로 회귀 방지를 위해 분리. */


export function indexAdongsByCode(
  adongs: AdongScore[],
): Record<string, AdongScore> {
  const m: Record<string, AdongScore> = {};
  for (const d of adongs) m[d.code] = d;
  return m;
}



export default function HeatMap({
  adongs,
  onAdongClick,
  heatmapVisible = true,
  activeLayer = 'composite',
  children,
  regionLevel = 'adong',
  selectedRegionSlug = null,
  selectedRegionLevel = regionLevel,
  selectedRegionAdongs,
  selectedRegionFocusKey = null,
  initialCenter,
  initialZoom,
}: HeatMapProps) {
  const { theme } = useTheme();
  const { data: seoulMaskGeojson, isLoading: maskLoading } = useSeoulMaskGeoJson();
  const [backgroundGeoEnabled, setBackgroundGeoEnabled] = useState(false);

  useEffect(() => {
    if (!seoulMaskGeojson || backgroundGeoEnabled) return;
    const timeoutId = window.setTimeout(() => setBackgroundGeoEnabled(true), 0);
    return () => window.clearTimeout(timeoutId);
  }, [backgroundGeoEnabled, seoulMaskGeojson]);

  const shouldFetchAdongGeo = backgroundGeoEnabled && (
    (heatmapVisible && regionLevel === 'adong')
    || (selectedRegionSlug != null && selectedRegionLevel === 'adong')
  );
  const shouldFetchLdongGeo = backgroundGeoEnabled && (
    (heatmapVisible && regionLevel === 'ldong')
    || (selectedRegionSlug != null && selectedRegionLevel === 'ldong')
  );
  const adongGeo = useAdongGeoJson({ enabled: shouldFetchAdongGeo });
  const ldongGeo = useLdongGeoJson({ enabled: shouldFetchLdongGeo });
  const geojson = regionLevel === 'ldong' ? ldongGeo.data : adongGeo.data;
  const selectedGeojson = selectedRegionLevel === 'ldong' ? ldongGeo.data : adongGeo.data;

  // GeoJSON 의 adm_cd2 (10자리 행정동 코드) 와 매칭하기 위해 code 키로 인덱싱.
  // (구버전은 adm_cd 7자리 ↔ slug 매칭이었으나 RDS 통합 후 한글 slug 라 깨짐.)
  const dongByCode = useMemo(() => indexAdongsByCode(adongs), [adongs]);
  const selectedDongByCode = useMemo(
    () => indexAdongsByCode(selectedRegionAdongs ?? adongs),
    [adongs, selectedRegionAdongs],
  );

  // 가중치/레이어/모드 변경마다 색이 갱신되도록 GeoJSON 레이어를 강제 리마운트.
  // 425개라 비용 약간 있지만 레이어 변경 빈도 낮아 OK.
  const layerKey = useMemo(() => {
    let acc = 0;
    for (const d of adongs) acc = (acc + Math.round((pickScore(d, activeLayer) ?? 0) * 100)) | 0;
    return `score-${regionLevel}-${activeLayer}-${adongs.length}-${selectedRegionSlug ?? 'none'}-${heatmapVisible ? 'heat' : 'outline'}-${acc}`;
  }, [adongs, activeLayer, heatmapVisible, regionLevel, selectedRegionSlug]);

  const scoreFillOpacity = 0.7;

  // DESIGN_SYSTEM.md "Map-Specific Shapes":
  //   - default polygon stroke: 1px white @ 60% opacity
  //   - heatmap fill opacity: 0.7 (score) / 0.85 (match — 모드 시각 차이)
  //   - cells without data: very faint Soft Stone wash
  const styleFn = (feature?: Feature<Geometry, AdongFeatureProps>) => {
    const code = feature?.properties?.adm_cd2 ?? '';

    if (!heatmapVisible) {
      return {
        color: 'transparent',
        weight: 0,
        opacity: 0,
        fillColor: 'transparent',
        fillOpacity: 0,
      };
    }

    const adong = dongByCode[code];
    const score = adong ? pickScore(adong, activeLayer) : null;
    const hasScore = isFiniteScore(score);
    return {
      color: MAP_POLYGON_STROKE.default.color,
      weight: MAP_POLYGON_STROKE.default.weight,
      opacity: MAP_POLYGON_STROKE.default.opacity,
      fillColor: hasScore ? scoreToHeatmapColor(score) : HEATMAP_NO_DATA,
      fillOpacity: hasScore ? scoreFillOpacity : 0.15,
    };
  };


  const maskStyle = {
    color: 'transparent',
    weight: 0,
    opacity: 0,
    fillColor: cssColorToken('--map-mask-fill'),
    fillOpacity: cssNumberToken('--map-mask-opacity', 0.5),
    fillRule: 'evenodd' as const,
    className: 'map-seoul-mask',
  };

  const layerLabel: Record<ScoreLayerKey, string> = {
    composite: '종합점수',
    rent: '전월세 점수',
    amenity: '생활시설 점수',
    transit: '교통 점수',
    safety: '안전 지수',
  };

  const onEachFeature = (
    feature: Feature<Geometry, AdongFeatureProps>,
    layer: Layer,
  ): void => {
    const code = feature.properties.adm_cd2 ?? '';
    const adong = dongByCode[code];
    if (!adong) return;
    if (!heatmapVisible) return;

    const shownScore = pickScore(adong, activeLayer);
    const scoreText = isFiniteScore(shownScore) ? shownScore.toFixed(1) : '데이터 없음';
    layer.bindTooltip(
      `<div class="map-tooltip__name">${adong.gu} · ${adong.name}</div>` +
        `<div class="map-tooltip__score tabular">${layerLabel[activeLayer]} ${scoreText}</div>`,
      { sticky: true, direction: 'top', offset: [0, -4], opacity: 1 },
    );

    const scoreForOpacity = pickScore(adong, activeLayer);
    const restingFillOpacity = isFiniteScore(scoreForOpacity) ? scoreFillOpacity : 0.15;

    layer.on({
      click: (e: LeafletMouseEvent) => {
        // Stop the click from bubbling to map.click — otherwise the kernel
        // score layer (Phase 2b) would also open. Polygon click → adong only.
        L.DomEvent.stopPropagation(e);
        onAdongClick?.(adong);
      },
      mouseover: (e) =>
        (e.target as { setStyle: (s: object) => void }).setStyle({
          fillOpacity: Math.min(1, restingFillOpacity + 0.1),
          weight: MAP_POLYGON_STROKE.hover.weight,
          opacity: MAP_POLYGON_STROKE.hover.opacity,
        }),
      mouseout: (e) =>
        (e.target as { setStyle: (s: object) => void }).setStyle({
          fillOpacity: restingFillOpacity,
          weight: MAP_POLYGON_STROKE.default.weight,
          opacity: MAP_POLYGON_STROKE.default.opacity,
        }),
    });
  };

  if (
    maskLoading
    || !seoulMaskGeojson
  ) {
    return (
      <div className="relative flex h-full w-full items-center justify-center bg-primary-soft text-[14px] font-semibold text-text-muted">
        지도 불러오는 중...
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={initialCenter ?? SEOUL_CITY_HALL}
        zoom={initialZoom ?? INITIAL_ZOOM}
        maxZoom={getVWorldMaxNativeZoom(theme)}
        zoomControl={false}
        scrollWheelZoom
        className="w-full h-full bg-surface-alt"
      >
        {/* VWorld tiles are capped at z=18 across themes to avoid broken high-zoom tiles. */}
        <TileLayer
          attribution={VWORLD_ATTRIBUTION}
          url={getVWorldTileUrl(theme)}
          maxZoom={getVWorldMaxNativeZoom(theme)}
          maxNativeZoom={getVWorldMaxNativeZoom(theme)}
        />
        <GeoJSON
          data={seoulMaskGeojson}
          style={maskStyle}
          interactive={false}
        />

        {selectedRegionSlug && selectedGeojson ? (
          <SelectedRegionBounds
            geojson={selectedGeojson}
            dongByCode={selectedDongByCode}
            selectedRegionSlug={selectedRegionSlug}
            focusKey={selectedRegionFocusKey}
          />
        ) : null}

        {heatmapVisible && geojson ? (
          <GeoJSON
            key={layerKey}
            data={geojson}
            style={styleFn}
            onEachFeature={onEachFeature}
          />
        ) : null}

        {selectedRegionSlug && selectedGeojson ? (
          <GeoJSON
            key={`selected-${selectedRegionLevel}-${selectedRegionSlug}-${selectedRegionFocusKey ?? 'stable'}`}
            data={selectedGeojson}
            style={(feature) => selectedRegionStyle(feature, selectedDongByCode, selectedRegionSlug)}
            interactive={false}
          />
        ) : null}

        {children}
      </MapContainer>
    </div>
  );
}

function selectedRegionStyle(
  feature: Feature<Geometry, AdongFeatureProps> | undefined,
  dongByCode: Record<string, AdongScore>,
  selectedRegionSlug: string,
) {
  const selected = feature ? isSelectedFeature(feature, dongByCode, selectedRegionSlug) : false;
  return {
    color: selected ? MAP_POLYGON_STROKE.selected.color : 'transparent',
    weight: selected ? 3 : 0,
    opacity: selected ? 1 : 0,
    fillColor: selected ? 'var(--color-heatmap-2)' : 'transparent',
    fillOpacity: selected ? 0.14 : 0,
  };
}

function SelectedRegionBounds({
  geojson,
  dongByCode,
  selectedRegionSlug,
  focusKey,
}: {
  geojson: AdongFeatureCollection;
  dongByCode: Record<string, AdongScore>;
  selectedRegionSlug: string;
  focusKey?: string | null;
}) {
  const map = useMap();

  useEffect(() => {
    const feature = geojson.features.find((item) => {
      return isSelectedFeature(item, dongByCode, selectedRegionSlug);
    });
    if (!feature) return;
    const bounds = L.geoJSON(feature).getBounds();
    if (!bounds.isValid()) return;
    map.fitBounds(bounds, { animate: true, padding: [36, 36], maxZoom: 15 });
  }, [dongByCode, focusKey, geojson, map, selectedRegionSlug]);

  return null;
}
