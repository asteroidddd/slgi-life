// HeroSection — top of adong detail page (SPEC 6.3 Section 1).
// Rebuilt for R-3 (design-polish-v2.md):
//
//   No <Card> wrapper anywhere — hero is its own composition. Height:
//   `min(520px, calc(100vh - 56px))` so first fold shows hero + start of
//   next section.
import { CircleMarker, MapContainer, TileLayer } from 'react-leaflet';

import { Button, MetricBar, Score } from '@/components/ui';
import { MAP_POLYGON_STROKE, scoreToHeatmapColor } from '@/lib/colors';
import type { AdongDetail, AdongScore } from '@/types/api';

import 'leaflet/dist/leaflet.css';

const VWORLD_KEY = import.meta.env.VITE_VWORLD_API_KEY as string | undefined;
const TILE_URL =
  VWORLD_KEY && VWORLD_KEY.length > 0
    ? `https://api.vworld.kr/req/wmts/1.0.0/${VWORLD_KEY}/Base/{z}/{y}/{x}.png`
    : 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
const TILE_ATTRIBUTION =
  VWORLD_KEY && VWORLD_KEY.length > 0
    ? '&copy; VWorld'
    : '&copy; OpenStreetMap &copy; CARTO';

interface HeroSectionProps {
  detail: AdongDetail;
  breakdown?: Pick<AdongScore, 'score_rent' | 'score_amenity' | 'score_transit'>;
  onAddCompare: () => void;
  onFavorite: () => void;
  onShare: () => void;
}

export default function HeroSection({
  detail,
  breakdown,
  onAddCompare,
  onFavorite,
  onShare,
}: HeroSectionProps) {
  const center: [number, number] = [detail.centroid.lat, detail.centroid.lng];
  const polygonColor = scoreToHeatmapColor(detail.score);

  return (
    <section
      className="min-h-[min(520px,calc(100vh-var(--space-14)))] flex flex-col gap-3 pt-8 pb-8"
      aria-label="동네 개요"
    >
      <p className="m-0 text-caption leading-[1.4] text-text-subtle tracking-normal">
        {detail.gu}
      </p>
      <h1 className="m-0 text-page-display leading-[1] font-bold text-text tracking-[-1.2px]">
        {detail.name}
      </h1>
      <p className="m-0 text-body-large leading-[1.5] text-text-subtle tracking-normal max-w-[60ch]">
        {detail.summary}
      </p>

      <div className="flex items-start justify-between gap-10 mt-4 flex-wrap">
        <div className="flex flex-col gap-5 flex-[1_1_320px] min-w-0">
          <Score
            value={Math.round(detail.score)}
            unit="/ 100"
            size="lg"
            ariaLabel={`${detail.name} 종합 점수 ${detail.score.toFixed(1)}점`}
          />
          {breakdown ? (
            <div className="flex flex-col gap-3 max-w-[360px]" aria-label="점수 구성">
              <MetricBar
                label="전월세"
                value={breakdown.score_rent}
                tone="score"
              />
              <MetricBar
                label="생활시설"
                value={breakdown.score_amenity}
                tone="score"
              />
              <MetricBar
                label="교통"
                value={breakdown.score_transit}
                tone="score"
              />
            </div>
          ) : (
            <div
              className="flex flex-col gap-3 max-w-[360px] min-h-[calc(var(--space-2)*3+var(--space-3)*2)]"
              aria-busy="true"
            />
          )}
        </div>

        <div className="flex flex-col gap-4 flex-[0_0_var(--hero-map-side)]">
          <div
            className="w-[var(--hero-map-side)] h-[var(--hero-map-side)] rounded-hero overflow-hidden bg-surface-alt"
            aria-label="동네 위치 미니 지도"
          >
            <MapContainer
              center={center}
              zoom={14}
              scrollWheelZoom={false}
              zoomControl={false}
              dragging={false}
              doubleClickZoom={false}
              className="w-full h-full"
              attributionControl={false}
            >
              <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} maxZoom={18} />
              <CircleMarker
                center={center}
                radius={10}
                pathOptions={{
                  color: MAP_POLYGON_STROKE.light,
                  weight: 2,
                  fillColor: polygonColor,
                  fillOpacity: 1,
                }}
              />
            </MapContainer>
          </div>

          <div className="flex flex-wrap gap-2" aria-label="동네 액션">
            <Button variant="secondary" size="md" onClick={onAddCompare}>
              비교에 추가
            </Button>
            <Button variant="secondary" size="md" onClick={onFavorite}>
              찜하기
            </Button>
            <Button variant="secondary" size="md" onClick={onShare}>
              공유
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
