// TransactionPinLayer -- renders RentDeal price chips on top of the heatmap.
//
// CSS classes (tx-chip, tx-chip__price, etc.) are rendered via Leaflet divIcon
// string HTML, so they cannot use Tailwind className. Styles are in globals.css
// under the Leaflet overrides section.

import { useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import { Marker, useMap, useMapEvents } from 'react-leaflet';

import type { Bbox, RentDealPin } from '@/types/api';

const MIN_ZOOM_FOR_PINS = 13;

const MOVE_DEBOUNCE_MS = 250;

type ChipVariant = 'compact' | 'standard' | 'expanded';

function chipVariantForZoom(zoom: number): ChipVariant {
  if (zoom >= 17) return 'expanded';
  if (zoom >= 15) return 'standard';
  return 'compact';
}

const VARIANT_SIZE: Record<ChipVariant, { w: number; h: number }> = {
  compact: { w: 28, h: 28 },
  standard: { w: 64, h: 30 },
  expanded: { w: 72, h: 44 },
};

export interface MapState {
  bbox: Bbox;
  zoom: number;
}

export interface TransactionPinLayerProps {
  pins: RentDealPin[];
  selectedJibun: string | null;
  onPinClick: (jibunKey: string, pin: RentDealPin) => void;
  onMapStateChange: (state: MapState) => void;
  suppressTooltips?: boolean;
}

function jibunKeyOf(p: RentDealPin): string {
  return `${p.gu}|${p.dong_name}|${p.jibun}`;
}

function roundMan(v: number): number {
  return Math.round(v);
}

function chipHtml(opts: {
  variant: ChipVariant;
  isSelected: boolean;
  isDimmed: boolean;
  avgConverted: number | null;
  count: number;
}): string {
  const { variant, isSelected, isDimmed, avgConverted, count } = opts;

  const priceText =
    avgConverted == null
      ? '?'
      : variant === 'compact'
        ? `${avgConverted}`
        : `${avgConverted}만원`;

  const sub =
    variant === 'expanded'
      ? `<span class="tx-chip__sub">${count}건</span>`
      : '';

  const cls = [
    'tx-chip',
    `tx-chip--${variant}`,
    isSelected ? 'tx-chip--selected' : '',
    isDimmed ? 'tx-chip--dimmed' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return `<div class="${cls}"><span class="tx-chip__price">${priceText}</span>${sub}<span class="tx-chip__pointer" aria-hidden="true"></span></div>`;
}

export default function TransactionPinLayer({
  pins,
  selectedJibun,
  onPinClick,
  onMapStateChange,
  suppressTooltips = false,
}: TransactionPinLayerProps) {
  const map = useMap();
  const debounceTimer = useRef<number | null>(null);
  const [zoom, setZoom] = useState<number>(() => map.getZoom());

  useEffect(() => {
    const b = map.getBounds();
    onMapStateChange({
      bbox: {
        lng1: b.getWest(),
        lat1: b.getSouth(),
        lng2: b.getEast(),
        lat2: b.getNorth(),
      },
      zoom: map.getZoom(),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useMapEvents({
    moveend: () => scheduleEmit(),
    zoomend: () => {
      setZoom(map.getZoom());
      scheduleEmit();
    },
  });

  function scheduleEmit() {
    if (debounceTimer.current != null) {
      window.clearTimeout(debounceTimer.current);
    }
    debounceTimer.current = window.setTimeout(() => {
      const b = map.getBounds();
      onMapStateChange({
        bbox: {
          lng1: b.getWest(),
          lat1: b.getSouth(),
          lng2: b.getEast(),
          lat2: b.getNorth(),
        },
        zoom: map.getZoom(),
      });
      debounceTimer.current = null;
    }, MOVE_DEBOUNCE_MS);
  }

  useEffect(
    () => () => {
      if (debounceTimer.current != null) {
        window.clearTimeout(debounceTimer.current);
      }
    },
    []
  );

  const groups = useMemo(() => {
    interface Group {
      key: string;
      pin: RentDealPin;
      count: number;
      convertedSum: number;
      convertedSamples: number;
    }
    const m = new Map<string, Group>();
    for (const p of pins) {
      const key = jibunKeyOf(p);
      const existing = m.get(key);
      const conv = typeof p.converted_rent === 'number' ? p.converted_rent : null;
      if (existing) {
        existing.count += 1;
        if (conv != null) {
          existing.convertedSum += conv;
          existing.convertedSamples += 1;
        }
      } else {
        m.set(key, {
          key,
          pin: p,
          count: 1,
          convertedSum: conv ?? 0,
          convertedSamples: conv != null ? 1 : 0,
        });
      }
    }
    return Array.from(m.values()).map((g) => ({
      key: g.key,
      pin: g.pin,
      count: g.count,
      avgConverted:
        g.convertedSamples > 0 ? roundMan(g.convertedSum / g.convertedSamples) : null,
    }));
  }, [pins]);

  if (zoom < MIN_ZOOM_FOR_PINS) return null;

  const variant = chipVariantForZoom(zoom);
  const size = VARIANT_SIZE[variant];

  return (
    <>
      {groups.map(({ key, pin, count, avgConverted }) => {
        const isSelected = selectedJibun === key;
        const isDimmed = suppressTooltips && !isSelected;

        const icon = L.divIcon({
          className: 'tx-chip-icon',
          html: chipHtml({
            variant,
            isSelected,
            isDimmed,
            avgConverted,
            count,
          }),
          iconSize: [size.w, size.h],
          iconAnchor: [size.w / 2, size.h],
        });

        return (
          <Marker
            key={key}
            position={[pin.lat, pin.lng]}
            icon={icon}
            zIndexOffset={isSelected ? 1000 : isDimmed ? -100 : 0}
            bubblingMouseEvents={false}
            eventHandlers={{
              click: (e) => {
                e.originalEvent.stopPropagation();
                onPinClick(key, pin);
              },
            }}
          />
        );
      })}
    </>
  );
}

export { MIN_ZOOM_FOR_PINS, jibunKeyOf };
