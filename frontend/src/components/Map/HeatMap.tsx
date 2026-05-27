// Leaflet 기반 행정동 히트맵 (SPEC 6.1) — VWorld 타일.
//
// 카카오맵 SDK 통합이 폴리곤 렌더링에서 일관성 문제를 일으켜 다시 Leaflet으로
// 복원. 타일은 VWorld(국토교통부) — 한국어 지명·도로·지하철이 OSM보다 풍부.
//
// /seoul_dongs.geojson 정적 파일에서 425개 행정동 경계를 1회 로드하고
// feature.properties.adm_cd2 (10자리 행정동 코드) === adong.code 로 score 데이터와 조인.
//
// VWorld 키: frontend/.env 의 VITE_VWORLD_API_KEY.
//   - 키 없으면 CartoDB Voyager 타일로 폴백 (시각적으로 무난, 그러나 한국어 라벨 약함).
//   - 키 발급: https://www.vworld.kr/ (회원가입 → 인증키 신청 → localhost 도메인 등록)

import { useMemo } from 'react';
import type { ReactNode } from 'react';
import L from 'leaflet';
import type { Layer, LeafletMouseEvent } from 'leaflet';
import type { Feature, Geometry } from 'geojson';
import { GeoJSON, MapContainer, TileLayer, ZoomControl } from 'react-leaflet';

import { useAdongGeoJson } from '@/hooks/useAdongGeoJson';
import { useSeoulMaskGeoJson } from '@/hooks/useSeoulMaskGeoJson';
import type { AdongFeatureProps } from '@/hooks/useAdongGeoJson';
import { HEATMAP_NO_DATA, MAP_POLYGON_STROKE, scoreToHeatmapColor } from '@/lib/colors';
import type { AdongScore, MatchCountItem } from '@/types/api';

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

const VWORLD_KEY = import.meta.env.VITE_VWORLD_API_KEY as string | undefined;

// VWorld WMTS Base 타일 (한국 지명·지하철·도로 풍부).
const VWORLD_TILE_URL =
  VWORLD_KEY && VWORLD_KEY.length > 0
    ? `https://api.vworld.kr/req/wmts/1.0.0/${VWORLD_KEY}/Base/{z}/{y}/{x}.png`
    : 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';

const VWORLD_ATTRIBUTION =
  VWORLD_KEY && VWORLD_KEY.length > 0
    ? '&copy; <a href="https://www.vworld.kr/">V-World</a> 국토교통부'
    : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/** 레이어 탭 — 색상의 기준이 되는 점수 축. score 모드 전용.
 *  Phase 5 cleanup 이후 호출측 (MainMap) 은 항상 'composite' 로 고정 사용 —
 *  단일 축 (rent/amenity/transit) 보기는 WEIGHTS 100/0/0 프리셋 칩으로 흡수.
 *  rent/amenity/transit 키는 pickScore unit test 와 잠재적 상세 화면 재사용을
 *  위해 type 에 그대로 보존. */
export type ScoreLayerKey = 'composite' | 'rent' | 'amenity' | 'transit';

/** 히트맵 색칠 모드.
 *  - 'score': activeLayer 의 점수 (composite/rent/amenity/transit) 기반.
 *  - 'match': MatchCountItem.ratio (0~100, log scale 정규화) 기반.
 *  Phase 5 default 는 'match' (자취생 첫 화면이 자기 조건으로 즉시 시작). */
export type HeatMapMode = 'score' | 'match';

export interface HeatMapProps {
  /** score 모드용 데이터. match 모드에서도 click handler 의 adong 인자에 필요. */
  adongs: AdongScore[];
  onAdongClick?: (adong: AdongScore) => void;
  /** 히트맵 폴리곤 표시 여부. false면 베이스맵만 보임. */
  heatmapVisible?: boolean;
  /** 색상 기준이 되는 점수 축. 기본 'composite' (가중합). score 모드에서만 사용. */
  activeLayer?: ScoreLayerKey;
  /** Phase 5: 'score' (기존) 또는 'match' (조건 거래량). default 'match'. */
  mode?: HeatMapMode;
  /** match 모드에서 폴리곤 색칠에 쓰는 카운트 분포. mode='match' 일 때만 의미. */
  matchCounts?: MatchCountItem[];
  /** 추가 레이어를 MapContainer 내부에 렌더링. react-leaflet 컴포넌트만 (e.g.,
   *  CircleMarker, useMap 사용 컴포넌트). 일반 DOM 노드는 작동 안 함. */
  children?: ReactNode;
}

export function pickScore(d: AdongScore, layer: ScoreLayerKey): number {
  switch (layer) {
    case 'rent':
      return d.score_rent;
    case 'amenity':
      return d.score_amenity;
    case 'transit':
      return d.score_transit;
    case 'composite':
    default:
      return d.score;
  }
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
  mode = 'match',
  matchCounts,
  children,
}: HeatMapProps) {
  const { data: geojson, isLoading: geoLoading } = useAdongGeoJson();
  const { data: seoulMaskGeojson, isLoading: maskLoading } = useSeoulMaskGeoJson();

  // GeoJSON 의 adm_cd2 (10자리 행정동 코드) 와 매칭하기 위해 code 키로 인덱싱.
  // (구버전은 adm_cd 7자리 ↔ slug 매칭이었으나 RDS 통합 후 한글 slug 라 깨짐.)
  const dongByCode = useMemo(() => indexAdongsByCode(adongs), [adongs]);

  // match 모드용 — code 키로 인덱싱한 MatchCountItem 맵.
  const matchByCode = useMemo(() => {
    const m: Record<string, MatchCountItem> = {};
    for (const item of matchCounts ?? []) m[item.code] = item;
    return m;
  }, [matchCounts]);

  // 가중치/레이어/모드 변경마다 색이 갱신되도록 GeoJSON 레이어를 강제 리마운트.
  // 425개라 비용 약간 있지만 슬라이더 빈도 낮아 OK.
  // mode 도 키에 포함 (eng-review 회귀 가드 — score↔match 토글 시 리마운트).
  const layerKey = useMemo(() => {
    let acc = 0;
    if (mode === 'score') {
      for (const d of adongs) acc = (acc + Math.round(pickScore(d, activeLayer) * 100)) | 0;
      return `score-${activeLayer}-${adongs.length}-${acc}`;
    }
    // match — ratio 기반 키 (정수 부분만 충분).
    // adongs가 비어 있는 초기 렌더 이후 score 데이터가 도착하면 GeoJSON을
    // 다시 마운트해야 polygon 클릭 핸들러가 붙는다.
    for (const d of adongs) acc = (acc + Number(d.code.slice(-4) || 0)) | 0;
    for (const item of matchCounts ?? []) {
      acc = (acc + Math.round(item.ratio * 10)) | 0;
    }
    return `match-${adongs.length}-${matchCounts?.length ?? 0}-${acc}`;
  }, [adongs, activeLayer, mode, matchCounts]);

  // match 모드 fillOpacity — 0.85 (eng-review #15 모드 시각 차이).
  const matchFillOpacity = 0.85;
  const scoreFillOpacity = 0.7;

  // DESIGN_SYSTEM.md "Map-Specific Shapes":
  //   - default polygon stroke: 1px white @ 60% opacity
  //   - heatmap fill opacity: 0.7 (score) / 0.85 (match — 모드 시각 차이)
  //   - cells without data: very faint Soft Stone wash
  const styleFn = (feature?: Feature<Geometry, AdongFeatureProps>) => {
    const code = feature?.properties?.adm_cd2 ?? '';

    if (mode === 'match') {
      const item = matchByCode[code];
      // has_data=false 또는 ratio===0 → NO_DATA 색 (Soft Stone 70% opacity).
      const hasColor = item != null && item.has_data && item.ratio > 0;
      return {
        color: MAP_POLYGON_STROKE.default.color,
        weight: MAP_POLYGON_STROKE.default.weight,
        opacity: MAP_POLYGON_STROKE.default.opacity,
        fillColor: hasColor ? scoreToHeatmapColor(item.ratio) : HEATMAP_NO_DATA,
        fillOpacity: hasColor ? matchFillOpacity : 0.7 * 0.5,
      };
    }

    const adong = dongByCode[code];
    const score = adong ? pickScore(adong, activeLayer) : null;
    return {
      color: MAP_POLYGON_STROKE.default.color,
      weight: MAP_POLYGON_STROKE.default.weight,
      opacity: MAP_POLYGON_STROKE.default.opacity,
      fillColor: score !== null ? scoreToHeatmapColor(score) : HEATMAP_NO_DATA,
      fillOpacity: score !== null ? scoreFillOpacity : 0.15,
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
  };

  const onEachFeature = (
    feature: Feature<Geometry, AdongFeatureProps>,
    layer: Layer,
  ): void => {
    const code = feature.properties.adm_cd2 ?? '';
    const adong = dongByCode[code];
    if (!adong) return;

    if (mode === 'match') {
      const item = matchByCode[code];
      const countLabel =
        item != null
          ? `${item.count.toLocaleString()}건`
          : '데이터 없음';
      layer.bindTooltip(
        `<div class="map-tooltip__name">${adong.gu} · ${adong.name}</div>` +
          `<div class="map-tooltip__score tabular">조건 매칭 ${countLabel}</div>`,
        { sticky: true, direction: 'top', offset: [0, -4], opacity: 1 },
      );
    } else {
      const shownScore = pickScore(adong, activeLayer);
      layer.bindTooltip(
        `<div class="map-tooltip__name">${adong.gu} · ${adong.name}</div>` +
          `<div class="map-tooltip__score tabular">${layerLabel[activeLayer]} ${shownScore.toFixed(1)}</div>`,
        { sticky: true, direction: 'top', offset: [0, -4], opacity: 1 },
      );
    }

    const item = matchByCode[code];
    const hasMatchColor = item != null && item.has_data && item.ratio > 0;
    const restingFillOpacity = mode === 'match'
      ? hasMatchColor ? matchFillOpacity : 0.7 * 0.5
      : scoreFillOpacity;

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

  if (geoLoading || maskLoading || !geojson || !seoulMaskGeojson) {
    return (
      <div className="relative flex h-full w-full items-center justify-center bg-primary-soft text-[14px] font-semibold text-text-muted">
        지도 불러오는 중...
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={SEOUL_CITY_HALL}
        zoom={INITIAL_ZOOM}
        maxZoom={19}
        zoomControl={false}
        scrollWheelZoom
        className="w-full h-full bg-surface-alt"
      >
        {/* maxZoom 19까지 허용 — VWorld Base 타일이 z=19까지 응답 (서울 전역 OK).
         *  타일 누락 시 Leaflet이 자동으로 z=18 타일을 stretch — 빈 영역 X. */}
        <TileLayer attribution={VWORLD_ATTRIBUTION} url={VWORLD_TILE_URL} maxZoom={19} />
        <ZoomControl position="topright" />
        <GeoJSON
          data={seoulMaskGeojson}
          style={maskStyle}
          interactive={false}
        />

        {heatmapVisible ? (
          <GeoJSON
            key={layerKey}
            data={geojson}
            style={styleFn}
            onEachFeature={onEachFeature}
          />
        ) : null}

        {children}
      </MapContainer>
    </div>
  );
}
