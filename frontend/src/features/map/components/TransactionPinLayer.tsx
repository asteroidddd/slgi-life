// TransactionPinLayer -- renders RentDeal price chips on top of the heatmap.
//
// CSS classes (tx-chip, tx-chip__price, etc.) are rendered via Leaflet divIcon
// string HTML, so they cannot use Tailwind className. Styles are in globals.css
// under the Leaflet overrides section.

import { useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import { Marker, useMap, useMapEvents } from 'react-leaflet';

import { formatManwonAmount } from '@/features/real-estate/lib/rent';
import type { Bbox, RentDealCachePin, RentDealPin, RentDealSummaryPin } from '@/features/common/types/api';

const MIN_ZOOM_FOR_PINS = 12;

const MOVE_DEBOUNCE_MS = 250;

type ChipVariant = 'compact' | 'standard' | 'expanded';

function chipVariantForZoom(zoom: number): ChipVariant {
  if (zoom >= 17) return 'expanded';
  if (zoom >= 15) return 'standard';
  return 'compact';
}

const VARIANT_SIZE: Record<ChipVariant, { w: number; h: number }> = {
  compact: { w: 96, h: 52 },
  standard: { w: 116, h: 62 },
  expanded: { w: 144, h: 82 },
};

export interface MapState {
  bbox: Bbox;
  zoom: number;
}

export interface TransactionPinLayerProps {
  pins: RentDealMapPin[];
  selectedJibun: string | null;
  onPinClick: (jibunKey: string, pin: RentDealMapPin) => void;
  onMapStateChange: (state: MapState) => void;
  suppressTooltips?: boolean;
}

export type RentDealMapPin = RentDealPin | RentDealCachePin | RentDealSummaryPin;

function hasAddress(p: RentDealMapPin): p is RentDealPin {
  return 'gu' in p && 'dong_name' in p && 'jibun' in p;
}

function isSummaryPin(p: RentDealMapPin): p is RentDealSummaryPin {
  return 'kind' in p;
}

function pinKeyOf(p: RentDealMapPin): string {
  if (isSummaryPin(p)) return `${p.kind}:${p.id}`;
  if (!hasAddress(p)) return `${p.lng.toFixed(5)}|${p.lat.toFixed(5)}`;
  return `${p.gu}|${p.dong_name}|${p.jibun}`;
}

const jibunKeyOf = pinKeyOf;

function bucketPrecisionForZoom(zoom: number): number {
  if (zoom >= 17) return 5;
  if (zoom >= 15) return 4;
  return 3;
}

function mapKeyOf(p: RentDealMapPin, zoom: number): string {
  if (isSummaryPin(p)) return `${p.kind}:${p.id}`;
  if (hasAddress(p)) return `${p.gu}|${p.dong_name}|${p.jibun}`;
  const precision = bucketPrecisionForZoom(zoom);
  return `${p.lng.toFixed(precision)}|${p.lat.toFixed(precision)}`;
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[mid];
  return (sorted[mid - 1] + sorted[mid]) / 2;
}

function avg(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function typeLabel(type: RentDealMapPin['deal_type']): string {
  switch (type) {
    case 'apt':
      return '아파트';
    case 'officetel':
      return '오피스텔';
    case 'yeonlip':
      return '연립';
    case 'dasedae':
      return '다세대';
    case 'yeonlip_dasedae':
    case 'villa':
      return '연립다세대';
    case 'dagagu':
      return '다가구';
    case 'danok':
      return '단독';
    case 'danok_dagagu':
      return '단독다가구';
    default:
      return '거래';
  }
}

function formatYmd(ymd: number | null): string {
  if (ymd == null || !Number.isFinite(ymd)) return '';
  const raw = String(Math.trunc(ymd));
  if (raw.length !== 8) return '';
  return `${raw.slice(2, 4)}.${raw.slice(4, 6)}.${raw.slice(6, 8)}`;
}

function chipHtml(opts: {
  variant: ChipVariant;
  isSelected: boolean;
  isDimmed: boolean;
  summary: GroupSummary;
}): string {
  const { variant, isSelected, isDimmed, summary } = opts;
  const priceText = formatManwonAmount(summary.medianConverted);
  const countText = `${summary.count.toLocaleString()}건`;
  const labelText = summary.label ?? '';
  const typeText = summary.primaryType ? typeLabel(summary.primaryType) : '거래';
  const areaText = summary.avgArea == null ? '-' : `평균 ${Math.round(summary.avgArea)}m²`;
  const depositText = `보증금 ${formatManwonAmount(summary.medianDeposit)}`;
  const latestText = formatYmd(summary.latestContractYmd);

  const cls = [
    'tx-chip',
    `tx-chip--${variant}`,
    isSelected ? 'tx-chip--selected' : '',
    isDimmed ? 'tx-chip--dimmed' : '',
  ]
    .filter(Boolean)
    .join(' ');

  if (variant === 'compact') {
    const top = labelText || priceText;
    const bottom = labelText ? `${priceText} · ${countText}` : countText;
    return `<div class="${cls}"><span class="tx-chip__price">${top}</span><span class="tx-chip__sub">${bottom}</span><span class="tx-chip__pointer" aria-hidden="true"></span></div>`;
  }
  if (variant === 'standard') {
    return `<div class="${cls}"><span class="tx-chip__price">${priceText}</span><span class="tx-chip__sub">${countText} · ${typeText}</span><span class="tx-chip__pointer" aria-hidden="true"></span></div>`;
  }
  return `<div class="${cls}"><span class="tx-chip__label">${priceText}</span><span class="tx-chip__sub">${countText} · ${areaText}</span><span class="tx-chip__meta">${depositText}${latestText ? ` · ${latestText}` : ''}</span><span class="tx-chip__pointer" aria-hidden="true"></span></div>`;
}

interface GroupSummary {
  count: number;
  medianConverted: number | null;
  avgConverted: number | null;
  medianDeposit: number | null;
  avgMonthlyRent: number | null;
  avgArea: number | null;
  latestContractYmd: number | null;
  primaryType: RentDealMapPin['deal_type'] | null;
  label?: string;
  kind?: 'ldong' | 'grid';
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
      pin: RentDealMapPin;
      items: RentDealMapPin[];
    }
    const m = new Map<string, Group>();
    for (const p of pins) {
      const key = mapKeyOf(p, zoom);
      const existing = m.get(key);
      if (existing) {
        existing.items.push(p);
      } else {
        m.set(key, {
          key,
          pin: p,
          items: [p],
        });
      }
    }
    return Array.from(m.values()).map((g) => {
      const converted = g.items
        .map((p) => p.converted_rent)
        .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
      const deposits = g.items
        .map((p) => p.deposit)
        .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
      const monthlyRents = g.items
        .map((p) => p.monthly_rent)
        .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
      const areas = g.items
        .map((p) => p.area_m2)
        .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
      const latestContractYmd = g.items.reduce<number | null>((latest, p) => {
        if (!('contract_ymd' in p)) return latest;
        if (latest == null || p.contract_ymd > latest) return p.contract_ymd;
        return latest;
      }, null);
      const typeCounts = new Map<RentDealMapPin['deal_type'], number>();
      for (const item of g.items) {
        typeCounts.set(item.deal_type, (typeCounts.get(item.deal_type) ?? 0) + 1);
      }
      const primaryType = Array.from(typeCounts.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
      return {
        key: g.key,
        pin: g.pin,
        summary: {
          count: g.items.reduce((sum, p) => sum + (isSummaryPin(p) ? p.count : 1), 0),
          medianConverted: median(converted),
          avgConverted: avg(converted),
          medianDeposit: median(deposits),
          avgMonthlyRent: avg(monthlyRents),
          avgArea: avg(areas),
          latestContractYmd,
          primaryType,
          label: isSummaryPin(g.pin) ? g.pin.label : undefined,
          kind: isSummaryPin(g.pin) ? g.pin.kind : undefined,
        } satisfies GroupSummary,
      };
    });
  }, [pins, zoom]);

  if (zoom < MIN_ZOOM_FOR_PINS) return null;

  const variant = chipVariantForZoom(zoom);
  const size = VARIANT_SIZE[variant];

  return (
    <>
      {groups.map(({ key, pin, summary }) => {
        const isSelected = selectedJibun === key;
        const isDimmed = suppressTooltips && !isSelected;

        const icon = L.divIcon({
          className: 'tx-chip-icon',
          html: chipHtml({
            variant,
            isSelected,
            isDimmed,
            summary,
          }),
          iconSize: [size.w, size.h],
          iconAnchor: [size.w / 2, size.h],
        });

        return (
          <Marker
            key={key}
            position={[pin.lat, pin.lng]}
            icon={icon}
            zIndexOffset={isSelected ? 1400 : isDimmed ? 500 : 700}
            bubblingMouseEvents={false}
            eventHandlers={isSummaryPin(pin) ? undefined : {
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
