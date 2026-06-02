import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GeoJSON, ImageOverlay, MapContainer, Pane, TileLayer, useMap } from 'react-leaflet';
import * as L from 'leaflet';
import type { LatLngBoundsExpression, Map as LeafletMap } from 'leaflet';
import type { Feature, MultiPolygon, Polygon } from 'geojson';

import { useTheme } from '@/contexts/ThemeContext';
import { api } from '@/lib/api';
import { VWORLD_MAX_ZOOM, getVWorldMaxNativeZoom, getVWorldTileUrl } from '@/lib/vworld';
import { useAdongGeoJson, useLdongGeoJson } from '@/hooks/useAdongGeoJson';

import 'leaflet/dist/leaflet.css';

type RegionLevel = 'adong' | 'ldong';
type Tone = 'good' | 'bad' | 'info' | 'warn';

const CHART_TOOLTIP_CLASS = 'pointer-events-none absolute z-[3000] hidden min-w-[136px] rounded-[6px] border border-border bg-[var(--surface-overlay-bg)] px-2 py-1.5 text-center text-[12px] font-bold leading-5 text-text shadow-lg backdrop-blur-md group-hover:block group-focus-within:block';

interface SectionRegion {
  gu: string;
  name: string;
  score?: number | null;
  score_rent?: number | null;
  score_transit?: number | null;
  score_amenity?: number | null;
  score_safety?: number | null;
}

interface DashboardSectionsProps {
  region: SectionRegion | null;
  regionLevel: RegionLevel;
  slug: string | null;
}

interface OverviewMetric {
  key: string;
  value: string | number | null;
  unit?: string;
  tone?: Tone;
  badge?: string;
  description?: string;
}

interface QuickTake {
  label: string;
  tone?: Tone;
}

interface OverviewResponse {
  headline?: string;
  summary?: string;
  quicktakes?: QuickTake[];
  metrics?: OverviewMetric[];
  station_names?: string[];
  station_items?: TransitStationItem[];
  basis?: Record<string, unknown>;
}

interface SeriesItem {
  month?: string;
  time?: string;
  display_time?: string;
  service_minute?: number;
  count?: number;
  value?: number | null;
  congestion?: number | null;
}

interface VolumeTrendResponse {
  items: SeriesItem[];
  basis?: {
    max_monthly_count?: number;
  };
}

interface RentTrendSeries {
  housing_type: string;
  items: Array<{
    month: string;
    week?: string;
    period?: string;
    value: number | null;
  }>;
}

interface RentTrendResponse {
  series?: RentTrendSeries[];
  basis?: Record<string, unknown>;
}

interface RentSummaryResponse {
  overview?: OverviewResponse;
  volume_trend?: VolumeTrendResponse;
  rent_trend?: RentTrendResponse;
  housing_type_mix?: {
    items?: TypeMixItem[];
  };
  basis?: Record<string, unknown>;
}

interface TypeMixItem {
  housing_type?: string;
  category?: string;
  label?: string;
  count: number;
  ratio: number;
  density?: number;
  seoul_density?: number;
  delta?: number | null;
  composition_value?: number;
  display_value?: string;
  display_unit?: string;
  group_key?: string;
  group_label?: string;
}

interface CongestionSeries {
  key: string;
  label: string;
  mode: 'bus' | 'subway';
  day_type: string;
  axis?: {
    start_minute: number;
    end_minute: number;
    start_label?: string;
    end_label?: string;
  };
  items: Array<{
    time: string;
    display_time?: string;
    service_minute?: number;
    congestion: number | null;
  }>;
}

interface CongestionResponse {
  series?: CongestionSeries[];
  subway?: SeriesItem[];
  bus?: SeriesItem[];
}

interface TransitStationItem {
  name: string;
  distance_m?: number | null;
  lines?: string[];
}

interface SafetyGradeItem {
  key: string;
  label?: string;
  score: number | null;
  tone?: Tone;
  raw_value?: number | null;
  seoul_score?: number | null;
  seoul_raw_value?: number | null;
  unit?: string;
  direction?: string;
  interpretation?: string;
  date?: string | null;
}

interface SafetyWmsLayerResponse {
  key: string;
  name: string;
  region?: {
    type?: RegionLevel;
    code?: string;
    slug?: string;
    name?: string;
    bbox?: [number, number, number, number] | null;
  } | null;
}

interface DashboardCacheResponse {
  region?: Record<string, unknown>;
  intro?: string;
  rent_summary?: RentSummaryResponse;
  transit_summary?: {
    overview?: OverviewResponse;
    congestion?: CongestionResponse;
  };
  infra_summary?: {
    overview?: OverviewResponse;
    category_mix?: { items: TypeMixItem[]; groups?: unknown[] };
  };
  safety_summary?: {
    overview?: OverviewResponse;
    grades?: { items: SafetyGradeItem[] };
    wms?: SafetyWmsLayerResponse;
  };
  computed_at?: string;
}

interface ChartSeries {
  key: string;
  label: string;
  color?: string;
  items: Array<{
    label: string;
    value: number | null;
    tooltip?: string;
  }>;
}

function endpoint(section: string, regionLevel: RegionLevel, slug: string) {
  return `/dashboard/${section}?region_type=${regionLevel}&slug=${encodeURIComponent(slug)}`;
}

function useDashboardData<T>(key: string, path: string | null) {
  return useQuery({
    queryKey: ['dashboard-section', key, path],
    queryFn: async () => {
      const { data } = await api.get<T>(path!);
      return data;
    },
    enabled: !!path,
    staleTime: 300_000,
  });
}

function pickMetric(metrics: OverviewMetric[] | undefined, key: string) {
  return metrics?.find((metric) => metric.key === key);
}

function metricValue(metric: OverviewMetric | undefined, fallback = '-') {
  if (!metric || metric.value == null || metric.value === '') return fallback;
  const value = typeof metric.value === 'number'
    ? Number.isInteger(metric.value) ? metric.value.toLocaleString() : metric.value.toFixed(1)
    : metric.value;
  return `${value}${metric.unit ?? ''}`;
}

function formatMonth(month?: string) {
  if (!month) return '';
  const [, m] = month.split('-');
  return m ? `${Number(m)}월` : month;
}

function formatTrendLabel(label?: string) {
  if (!label) return '';
  const match = label.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match) return `${Number(match[2])}/${Number(match[3])}주`;
  return formatMonth(label) || label;
}

function maxNumber(items: number[]) {
  return Math.max(1, ...items.filter((value) => Number.isFinite(value)));
}

function clampPercent(value: number, max: number) {
  if (!Number.isFinite(value) || max <= 0) return 0;
  return Math.max(4, Math.min(100, (value / max) * 100));
}

function smoothLinePath(points: Array<{ x: number; y: number }>) {
  if (!points.length) return '';
  if (points.length === 1) return `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
  const parts = [`M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`];
  for (let index = 0; index < points.length - 1; index += 1) {
    const p0 = points[index - 1] ?? points[index];
    const p1 = points[index];
    const p2 = points[index + 1];
    const p3 = points[index + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    parts.push(`C${c1x.toFixed(1)} ${c1y.toFixed(1)},${c2x.toFixed(1)} ${c2y.toFixed(1)},${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`);
  }
  return parts.join(' ');
}

function useMeasuredWidth<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const element = ref.current;
    if (!element) return undefined;

    const update = () => setWidth(Math.max(0, Math.floor(element.getBoundingClientRect().width)));
    update();

    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', update);
      return () => window.removeEventListener('resize', update);
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      setWidth(Math.max(0, Math.floor(entry.contentRect.width)));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return [ref, width] as const;
}

function toneClass(tone: Tone | undefined) {
  switch (tone) {
    case 'good':
      return 'border-success/25 bg-success-soft text-success';
    case 'bad':
      return 'border-danger/25 bg-danger-soft text-danger';
    case 'warn':
      return 'border-warning-deep/25 bg-warning-soft text-warning-deep';
    case 'info':
    default:
      return 'border-info/20 bg-info-soft/45 text-info';
  }
}

function readableCategory(value?: string) {
  if (!value) return '';
  const map: Record<string, string> = {
    restaurant: '음식점',
    convenience: '편의점',
    mart: '슈퍼마켓',
    daiso: '다이소',
    cafe: '카페',
    nightlife: '주점',
    park: '공원',
    hospital: '병원',
    dental: '치과',
    pharmacy: '약국',
    bus_stop: '버스정류장',
    subway_station: '지하철역',
    library: '도서관',
    university: '대학교',
    gym: '헬스장',
    beauty: '미용',
    laundry: '세탁',
    book_stationery: '서점/문구',
    study_cafe: '스터디카페/독서실',
    pc_room: 'PC방',
    oliveyoung: '올리브영',
    etc: '기타',
  };
  return map[value] ?? value;
}

function SectionHeader({
  kicker,
  title,
  summary,
  children,
  info,
}: {
  kicker: string;
  title: string;
  summary: string;
  children?: ReactNode;
  info?: string;
}) {
  return (
    <div className="grid gap-2">
      <div className="flex items-start justify-between gap-5">
        <div className="min-w-0">
          <p className="m-0 text-[13px] font-bold text-[var(--color-heatmap-5)]">{kicker}</p>
          <h2 className="m-0 mt-1 text-[24px] font-bold leading-tight text-text">{title}</h2>
        </div>
        {children || info ? (
          <div className="grid max-w-[460px] shrink-0 justify-items-end gap-2">
            {info ? <InfoButton text={info} /> : null}
            {children ? <div className="flex flex-wrap justify-end gap-1.5">{children}</div> : null}
          </div>
        ) : null}
      </div>
      <p className="m-0 max-w-none text-[14px] leading-6 text-text-muted">{summary}</p>
    </div>
  );
}

function SummaryCluster({ quicktakes, note }: { quicktakes?: QuickTake[]; note?: string }) {
  return (
    <div className="grid justify-items-end gap-1.5 text-right">
      <div className="flex flex-wrap justify-end gap-1.5">
        {(quicktakes ?? []).slice(0, 4).map((item) => (
          <span key={item.label} className={`inline-flex min-h-7 items-center rounded-full border px-3 text-[12px] font-bold ${toneClass(item.tone)}`}>
            {item.label}
          </span>
        ))}
      </div>
      {note ? <p className="m-0 max-w-[380px] text-[12px] font-medium leading-5 text-text-muted">{note}</p> : null}
    </div>
  );
}

function InfoButton({ text }: { text: string }) {
  return (
    <span className="group relative z-[80] inline-flex">
      <button type="button" aria-label="추가 정보" className="grid h-5 w-5 place-items-center rounded-full border border-border bg-transparent text-[11px] font-bold text-text-muted hover:border-text-muted hover:text-text">
        i
      </button>
      <span className="pointer-events-none absolute right-0 top-[calc(100%+6px)] z-[90] hidden w-[300px] whitespace-pre-line rounded-[6px] border border-border bg-[var(--surface-overlay-bg)] p-3 text-left text-[12px] font-semibold leading-5 text-text-muted shadow-lg backdrop-blur-md group-hover:block group-focus-within:block">
        {text}
      </span>
    </span>
  );
}

function MetricGrid({
  items,
  className = 'mt-4 grid grid-cols-4 gap-3',
  itemClassName = '',
}: {
  items: Array<{ label: string; value: string; badge: string; tone?: Tone; note: string }>;
  className?: string;
  itemClassName?: string;
}) {
  return (
    <div className={className}>
      {items.map((item) => (
        <article key={item.label} className={`relative min-h-[104px] rounded-card border border-border bg-surface-alt p-4 ${itemClassName}`}>
          <span className={`absolute right-3 top-3 rounded-full border px-2 py-1 text-[11px] font-bold leading-none ${toneClass(item.tone)}`}>{item.badge}</span>
          <p className="m-0 pr-16 text-[12px] font-bold text-text-muted">{item.label}</p>
          <strong className="mt-3 block text-[23px] font-bold leading-none text-text">{item.value}</strong>
          <small className="mt-2 block text-[12px] font-semibold leading-5 text-text-muted">{item.note}</small>
        </article>
      ))}
    </div>
  );
}

function formatStationDistance(distance?: number | null) {
  if (typeof distance !== 'number' || !Number.isFinite(distance)) return null;
  if (distance <= 0) return '동 내';
  if (distance < 1000) return `${Math.round(distance)}m`;
  return `${(distance / 1000).toFixed(1)}km`;
}

function TransitStationList({ stations, stationItems }: { stations?: string[]; stationItems?: TransitStationItem[] }) {
  const rows: TransitStationItem[] = (stationItems?.length
    ? stationItems
    : Array.from(new Set(stations ?? [])).map((name): TransitStationItem => ({
        name,
        lines: [],
        distance_m: null,
      }))
  ).sort((a, b) => {
    const distanceA = typeof a.distance_m === 'number' ? a.distance_m : Number.POSITIVE_INFINITY;
    const distanceB = typeof b.distance_m === 'number' ? b.distance_m : Number.POSITIVE_INFINITY;
    if (distanceA !== distanceB) return distanceA - distanceB;
    return a.name.localeCompare(b.name, 'ko');
  });
  const visible = rows.slice(0, 5);
  return (
    <article className="h-full min-h-0 overflow-hidden rounded-card border border-border bg-surface-alt p-4">
      <p className="m-0 pr-16 text-[12px] font-bold text-text-muted">1km 이내 지하철역</p>
      <div className="mt-2 grid gap-1 overflow-hidden">
        {visible.length ? visible.map((station) => {
          const distanceLabel = formatStationDistance(station.distance_m);
          return (
            <div key={station.name} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 px-0 py-0.5">
              <span className="min-w-0 truncate text-[12px] font-bold text-text">{station.name}</span>
              <span className="flex min-w-0 items-center justify-end gap-1.5 text-right">
                {distanceLabel ? <span className="shrink-0 text-[11px] font-bold text-text">{distanceLabel}</span> : null}
                <span className="max-w-[74px] truncate text-[11px] font-semibold text-text-muted">
                  {station.lines?.length ? station.lines.join(', ') : '-'}
                </span>
              </span>
            </div>
          );
        }) : (
          <span className="text-[12px] font-semibold text-text-muted">1km 이내 역 없음</span>
        )}
        {rows.length > visible.length ? (
          <div className="px-0 py-0.5 text-[12px] font-bold text-text-muted">...</div>
        ) : null}
      </div>
    </article>
  );
}

function Card({ title, hint, info, children, className = '' }: { title: string; hint?: string; info?: string; children: ReactNode; className?: string }) {
  return (
    <article className={`flex min-h-[248px] flex-col overflow-visible rounded-card border border-border bg-surface p-4 ${className}`}>
      <div className="relative z-[60] mb-3 flex items-start justify-between gap-3">
        <h3 className="m-0 text-[15px] font-bold text-text">{title}</h3>
        <div className="flex items-center gap-2">
          {hint ? <span className="text-right text-[12px] font-semibold text-text-muted">{hint}</span> : null}
          {info ? <InfoButton text={info} /> : null}
        </div>
      </div>
      {children}
    </article>
  );
}

function BarChart({ items, valueKey = 'count' }: { items: SeriesItem[]; valueKey?: 'count' | 'value' | 'congestion' }) {
  const values = items.map((item) => Number(item[valueKey] ?? 0));
  const max = maxNumber(values);
  return (
    <div className="relative z-[70] flex h-[138px] min-h-[138px] flex-1 items-end gap-2 overflow-visible border-b border-border px-1 pb-6">
      {items.map((item, index) => {
        const value = Number(item[valueKey] ?? 0);
        const label = formatMonth(item.month) || item.time || `${index + 1}`;
        const height = value <= 0 ? 0 : clampPercent(value, max);
        return (
          <div key={`${item.month ?? item.time ?? index}`} className="group relative flex h-full flex-1 flex-col items-center justify-end gap-2">
            <span className="w-full rounded-t-[var(--map-control-radius)] bg-[var(--color-heatmap-4)]/80 transition group-hover:bg-[var(--color-heatmap-5)]" style={{ height: `${height}%`, minHeight: value > 0 ? 10 : 0 }} />
            <span className="absolute bottom-[-22px] text-[11px] font-semibold text-text-muted">{label}</span>
            <span className="pointer-events-none absolute bottom-[calc(100%+8px)] left-1/2 z-[3000] hidden min-w-[136px] -translate-x-1/2 rounded-[6px] border border-border bg-[var(--surface-overlay-bg)] px-2 py-1.5 text-center text-[12px] font-bold leading-5 text-text shadow-lg backdrop-blur-md group-hover:block">
              {label}<br />
              거래 {value.toLocaleString()}건<br />
              <small className="font-semibold text-text-muted">표시 기준 최대 {max.toLocaleString()}건</small>
            </span>
          </div>
        );
      })}
    </div>
  );
}

function MultiSeriesLineChart({ series, emptyText, unit = '' }: { series: ChartSeries[]; emptyText: string; unit?: string }) {
  const [chartRef, measuredWidth] = useMeasuredWidth<HTMLDivElement>();
  const allLabels = Array.from(new Set(series.flatMap((line) => line.items.map((point) => point.label))));
  const labelsWithValues = allLabels.filter((label) => series.some((line) => {
    const point = line.items.find((item) => item.label === label);
    return typeof point?.value === 'number' && Number.isFinite(point.value);
  }));
  const labels = labelsWithValues.length ? labelsWithValues : allLabels;
  const values = series
    .flatMap((line) => line.items.map((point) => point.value))
    .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
  const yMinRaw = values.length ? Math.min(...values) : 0;
  const yMaxRaw = values.length ? Math.max(...values) : 1;
  const ySpread = Math.max(0.1, yMaxRaw - yMinRaw);
  const yMin = Math.max(0, yMinRaw - ySpread * 0.12);
  const yMax = yMaxRaw + ySpread * 0.12;
  const yTicks = [yMax, (yMin + yMax) / 2, yMin];
  const colors = ['#2f6f9f', '#7a5c99', '#4f8f7b', '#b7793f', '#5570F1', '#EF4444'];
  const width = Math.max(320, measuredWidth || 640);
  const height = 116;
  const plotLeft = 30;
  const plotRight = 1;
  const plotTop = 10;
  const plotBottom = 92;
  const plotWidth = width - plotLeft - plotRight;
  const xFor = (index: number) => (labels.length <= 1 ? plotLeft + plotWidth / 2 : plotLeft + (index / (labels.length - 1)) * plotWidth);
  const yFor = (value: number) => plotBottom - ((value - yMin) / Math.max(0.1, yMax - yMin)) * (plotBottom - plotTop);
  const formatY = (value: number) => (Math.abs(value) >= 10 ? value.toFixed(0) : value.toFixed(1));

  if (!series.length || !labels.length || !values.length) {
    return (
      <div className="grid min-h-[160px] flex-1 place-items-center rounded-[var(--map-control-radius)] border border-dashed border-border bg-surface-alt text-[13px] font-semibold text-text-muted">
        {emptyText}
      </div>
    );
  }

  return (
    <div ref={chartRef} className="mt-1 flex min-h-[164px] w-full min-w-0 flex-1 flex-col justify-between">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[132px] w-full overflow-visible" role="img" aria-label="다중 선 그래프">
        <line x1={plotLeft} y1={plotTop} x2={plotLeft} y2={plotBottom} stroke="var(--color-border)" strokeWidth="1" />
        {yTicks.map((tick) => {
          const y = yFor(tick);
          return (
            <g key={tick.toFixed(3)}>
              <line x1={plotLeft} y1={y} x2={width - plotRight} y2={y} stroke="var(--color-border)" strokeWidth="1" />
              <text x={plotLeft - 5} y={y} textAnchor="end" dominantBaseline="middle" className="fill-text-muted text-[9px] font-semibold">
                {formatY(tick)}
              </text>
            </g>
          );
        })}
        {series.map((line, lineIndex) => {
          const color = line.color ?? colors[lineIndex % colors.length];
          const pointMap = new Map(line.items.map((point) => [point.label, point]));
          const points = labels
            .map((label, labelIndex) => {
              const point = pointMap.get(label);
              if (typeof point?.value !== 'number' || !Number.isFinite(point.value)) return null;
              return { ...point, x: xFor(labelIndex), y: yFor(point.value) };
            })
            .filter((point): point is { label: string; value: number; tooltip?: string; x: number; y: number } => point != null);
          const path = points.map((point, pointIndex) => `${pointIndex === 0 ? 'M' : 'L'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' ');
          return (
            <g key={line.key}>
              {points.length > 1 ? (
                <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <title>{`${line.label} · ${unit}`}</title>
                </path>
              ) : null}
            </g>
          );
        })}
      </svg>
      <div className="flex justify-between text-[11px] font-semibold text-text-muted">
        <span>{formatTrendLabel(labels[0]) || labels[0]}</span>
        <span>{formatTrendLabel(labels[labels.length - 1]) || labels[labels.length - 1]}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {series.map((line, index) => (
          <span key={line.key} className="inline-flex items-center gap-1.5 text-[11px] font-bold text-text-muted">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: line.color ?? colors[index % colors.length] }} />
            {line.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function rentTrendSeries(data?: RentTrendSeries[]): ChartSeries[] {
  return (data ?? []).map((line) => ({
    key: line.housing_type,
    label: line.housing_type,
    items: line.items.map((point) => ({
      label: point.week ?? point.period ?? point.month,
      value: point.value,
      tooltip: `${line.housing_type} · ${formatTrendLabel(point.week ?? point.period ?? point.month)} · ${point.value == null ? '-' : point.value.toFixed(2)}만원/㎡`,
    })),
  }));
}

function timeToMinutes(time: string) {
  const [hour, minute] = time.split(':').map((value) => Number(value));
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) return 0;
  return hour * 60 + minute;
}

function formatAxisTime(minutes: number) {
  const raw = minutes % 1440;
  const hour = Math.floor(raw / 60);
  const minute = raw % 60;
  const text = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
  return minutes >= 1440 ? `익일 ${text}` : text;
}

function threeHourTicks(start: number, end: number) {
  const ticks = [start];
  const first = Math.ceil(start / 180) * 180;
  for (let tick = first; tick <= end; tick += 180) {
    if (tick - start < 180) continue;
    if (end - tick < 180) continue;
    ticks.push(tick);
  }
  if (!ticks.includes(end)) ticks.push(end);
  return Array.from(new Set(ticks)).sort((a, b) => a - b);
}

function CongestionLineChart({ series, mode }: { series?: CongestionSeries[]; mode: 'bus' | 'subway' }) {
  const [chartRef, measuredWidth] = useMeasuredWidth<HTMLDivElement>();
  const lines = (series ?? []).filter((line) => line.mode === mode);
  const points = lines.flatMap((line) => line.items.filter((item) => item.congestion != null));
  const values = points.map((point) => Number(point.congestion)).filter((value) => Number.isFinite(value));
  const width = Math.max(420, measuredWidth || 1120);
  const height = 148;
  const plot = { left: 24, right: 34, top: 12, bottom: 112 };
  const defaultStart = mode === 'subway' ? 330 : 240;
  const xMin = 240;
  const xMax = 1620;
  const yMinRaw = values.length ? Math.min(...values) : 0;
  const yMaxRaw = values.length ? Math.max(...values) : 1;
  const yPad = Math.max(8, (yMaxRaw - yMinRaw) * 0.18);
  const yMin = Math.max(0, Math.floor(yMinRaw - yPad));
  const yMax = Math.ceil(yMaxRaw + yPad);
  const colors = ['#2f6f9f', '#b7793f'];
  const serviceMinute = (item: { time: string; service_minute?: number }) => {
    if (typeof item.service_minute === 'number') return item.service_minute;
    const raw = timeToMinutes(item.time);
    return raw < defaultStart ? raw + 1440 : raw;
  };
  const xFor = (item: { time: string; service_minute?: number }) => {
    const minute = Math.max(xMin, Math.min(xMax, serviceMinute(item)));
    return plot.left + ((minute - xMin) / Math.max(1, xMax - xMin)) * (width - plot.left - plot.right);
  };
  const yFor = (value: number) => plot.bottom - ((value - yMin) / Math.max(1, yMax - yMin)) * (plot.bottom - plot.top);
  const ticks = threeHourTicks(xMin, xMax);

  if (!lines.length || !values.length) {
    return (
      <div className="grid h-[132px] place-items-center rounded-[var(--map-control-radius)] border border-dashed border-border bg-surface-alt text-[13px] font-semibold text-text-muted">
        혼잡도 데이터가 없습니다.
      </div>
    );
  }

  return (
    <div ref={chartRef} className="grid w-full min-w-0 gap-1">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full overflow-visible" style={{ height }} role="img" aria-label={`${mode === 'subway' ? '지하철' : '버스'} 혼잡도 흐름`}>
        {ticks.map((tick) => {
          const x = plot.left + ((tick - xMin) / Math.max(1, xMax - xMin)) * (width - plot.left - plot.right);
          return <line key={tick} x1={x} y1={plot.top} x2={x} y2={plot.bottom} stroke="var(--color-border)" strokeWidth="1" strokeDasharray="3 4" />;
        })}
        {[yMin, Math.round((yMin + yMax) / 2), yMax].map((tick) => {
          const y = yFor(tick);
          return (
            <g key={tick}>
              <line x1={plot.left} y1={y} x2={width - plot.right} y2={y} stroke="var(--color-border)" strokeWidth="1" />
              <text x={plot.left - 8} y={y} textAnchor="end" dominantBaseline="middle" className="fill-text-muted text-[10px] font-semibold">{tick}</text>
            </g>
          );
        })}
        {lines.map((line, index) => {
          const valid = line.items.filter((item) => item.congestion != null);
          const pointsForPath = valid.map((item) => ({ x: xFor(item), y: yFor(Number(item.congestion)) }));
          const d = smoothLinePath(pointsForPath);
          const color = colors[index % colors.length];
          return (
            <g key={line.key}>
              <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <title>{line.label}</title>
              </path>
            </g>
          );
        })}
        {ticks.map((tick) => {
          const x = plot.left + ((tick - xMin) / Math.max(1, xMax - xMin)) * (width - plot.left - plot.right);
          const anchor = tick === ticks[0] ? 'start' : tick === ticks[ticks.length - 1] ? 'end' : 'middle';
          return <text key={`label-${tick}`} x={x} y={height - 12} textAnchor={anchor} className="fill-text-muted text-[10px] font-semibold">{formatAxisTime(tick)}</text>;
        })}
      </svg>
      <div className="flex flex-wrap gap-2">
        {lines.map((line, index) => (
          <span key={line.key} className="inline-flex items-center gap-1.5 text-[11px] font-bold text-text-muted">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colors[index % colors.length] }} />
            {line.day_type}
          </span>
        ))}
      </div>
    </div>
  );
}

const INFRA_GROUPS = [
  { key: 'food', label: '식생활', categories: ['restaurant', 'cafe', 'convenience', 'mart', 'daiso', 'nightlife'] },
  { key: 'culture', label: '문화', categories: ['park', 'gym', 'beauty', 'oliveyoung', 'laundry'] },
  { key: 'study', label: '학습', categories: ['library', 'book_stationery', 'study_cafe'] },
  { key: 'medical', label: '의료', categories: ['hospital', 'dental', 'pharmacy'] },
];

function infraGroupRows(items: TypeMixItem[]) {
  const byCategory = new Map(items.map((item) => [item.category ?? item.housing_type ?? item.label ?? '', item]));
  return INFRA_GROUPS.map((group) => {
    const details = group.categories.map((category) => {
      const item = byCategory.get(category);
      const groupDensity = category === 'park' ? 0 : item?.density ?? 0;
      const groupSeoulDensity = category === 'park' ? 0 : item?.seoul_density ?? 0;
      return {
        category,
        label: readableCategory(category),
        count: item?.count ?? 0,
        density: groupDensity,
        seoulDensity: groupSeoulDensity,
      };
    });
    return {
      ...group,
      count: details.reduce((sum, item) => sum + item.count, 0),
      density: details.reduce((sum, item) => sum + item.density, 0),
      seoulDensity: details.reduce((sum, item) => sum + item.seoulDensity, 0),
      details,
    };
  });
}

function InfraDensityDotPlot({ items }: { items: TypeMixItem[] }) {
  const groups = infraGroupRows(items);
  const seoulPosition = 66.666;
  const xFor = (density: number, seoulDensity: number) => {
    if (!Number.isFinite(density) || !Number.isFinite(seoulDensity) || seoulDensity <= 0) {
      return seoulPosition;
    }
    return Math.max(4, Math.min(96, (density / seoulDensity) * seoulPosition));
  };
  return (
    <div className="grid min-h-[176px] flex-1 content-center gap-3">
      {groups.map((group) => (
        <div key={group.key} className="grid grid-cols-[54px_1fr_76px] items-center gap-3">
          <span className="text-[12px] font-bold text-text-muted">{group.label}</span>
          <div className="relative h-6 rounded-full bg-surface-alt">
            <span className="absolute top-1/2 h-4 w-px -translate-y-1/2 bg-border" style={{ left: `${seoulPosition}%` }} />
            <span
              className="group absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-[var(--color-heatmap-4)] shadow-sm"
              style={{ left: `${xFor(group.density, group.seoulDensity)}%` }}
              tabIndex={0}
            >
              <span className={`${CHART_TOOLTIP_CLASS} bottom-[calc(100%+12px)] left-1/2 -translate-x-1/2`}>
                {group.label}<br />
                선택 지역 {group.density.toFixed(1)}곳/km²<br />
                <small className="font-semibold text-text-muted">서울 기준 {group.seoulDensity.toFixed(1)}곳/km²</small>
              </span>
            </span>
          </div>
          <span className="text-right text-[12px] font-bold text-text">{group.density.toFixed(1)}</span>
        </div>
      ))}
      <div className="flex justify-end gap-4 text-[11px] font-semibold text-text-muted">
        <span><span className="mr-1 inline-block h-3 w-px translate-y-0.5 bg-border" />서울</span>
        <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-[var(--color-heatmap-4)]" />선택 지역</span>
      </div>
    </div>
  );
}

function InfraTreemap({ items }: { items: TypeMixItem[] }) {
  const valueFor = (item: TypeMixItem) => item.composition_value ?? item.density ?? item.count;
  const visible = items.filter((item) => valueFor(item) > 0).sort((a, b) => valueFor(b) - valueFor(a)).slice(0, 10);
  const total = visible.reduce((sum, item) => sum + valueFor(item), 0);
  if (!visible.length) {
    return <div className="grid min-h-[140px] place-items-center rounded-[var(--map-control-radius)] border border-dashed border-border bg-surface-alt text-[13px] font-semibold text-text-muted">시설 구성 데이터가 없습니다.</div>;
  }
  return (
    <div className="grid min-h-[150px] grid-cols-5 auto-rows-[64px] gap-2">
      {visible.map((item) => {
        const value = valueFor(item);
        const ratio = value / Math.max(1, total);
        const span = ratio >= 0.36 ? 'col-span-2 row-span-2' : ratio >= 0.14 ? 'col-span-2' : '';
        const displayValue = item.display_value ?? item.count.toLocaleString();
        const titleUnit = item.display_unit ? ` · ${item.display_unit}` : '';
        return (
          <div
            key={item.category}
            className={`grid min-h-0 content-between overflow-hidden rounded-[6px] border border-border bg-surface-alt p-2 ${span}`}
            title={`${readableCategory(item.category)} · ${displayValue}${titleUnit}`}
          >
            <span className="truncate text-[11px] font-bold text-text">{readableCategory(item.category)}</span>
            <span className="text-[15px] font-extrabold leading-none text-text">{displayValue}</span>
            <span className="truncate text-[10px] font-semibold text-text-muted">{item.group_label ?? ''}</span>
          </div>
        );
      })}
    </div>
  );
}

function InfraDivergingBars({ items }: { items: TypeMixItem[] }) {
  const valid = items.filter((item) => typeof item.delta === 'number' && Number.isFinite(item.delta));
  const strengths = valid.filter((item) => Number(item.delta) > 0).sort((a, b) => Number(b.delta) - Number(a.delta)).slice(0, 3);
  const weaknesses = valid
    .filter((item) => Number(item.delta) < 0)
    .sort((a, b) => Number(a.delta) - Number(b.delta))
    .slice(0, 3)
    .sort((a, b) => Number(b.delta) - Number(a.delta));
  const ranked = [...strengths, ...weaknesses];
  const positiveMax = Math.max(0.01, ...valid.filter((item) => Number(item.delta) > 0).map((item) => Number(item.delta)));
  const barWidth = (delta: number) => {
    const scale = delta < 0 ? 1 : positiveMax;
    return Math.max(6, Math.min(50, Math.abs(delta) / scale * 50));
  };
  if (!ranked.length) {
    return <div className="grid min-h-[168px] place-items-center rounded-[var(--map-control-radius)] border border-dashed border-border bg-surface-alt text-[13px] font-semibold text-text-muted">서울 평균 비교값이 없습니다.</div>;
  }
  const renderRows = (rows: TypeMixItem[], emptyText: string) => (
    rows.length ? rows.map((item) => {
      const delta = Number(item.delta);
      const width = barWidth(delta);
      return (
        <div key={item.category} className="grid grid-cols-[82px_1fr_58px] items-center gap-2 text-[12px]">
          <span className="truncate font-bold text-text-muted">{readableCategory(item.category)}</span>
          <div className="relative h-5 rounded-full bg-surface-alt">
            <span className="absolute left-1/2 top-0 h-full w-px bg-border" />
            <span
              className={`group absolute top-1/2 h-2.5 -translate-y-1/2 rounded-full ${delta >= 0 ? 'left-1/2 bg-[var(--color-success)]' : 'right-1/2 bg-[var(--color-danger)]'}`}
              style={{ width: `${width}%` }}
              tabIndex={0}
            >
              <span className={`${CHART_TOOLTIP_CLASS} bottom-[calc(100%+12px)] left-1/2 -translate-x-1/2`}>
                {readableCategory(item.category)}<br />
                서울 평균 대비 {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
              </span>
            </span>
          </div>
          <span className="text-right font-bold text-text">{delta >= 0 ? '+' : ''}{(delta * 100).toFixed(0)}%</span>
        </div>
      );
    }) : <div className="text-[12px] font-semibold text-text-muted">{emptyText}</div>
  );
  return (
    <div className="grid min-h-[176px] flex-1 content-center gap-2">
      {renderRows(strengths, '서울 평균보다 높은 시설이 없습니다.')}
      <div className="my-0.5 h-px bg-border" />
      {renderRows(weaknesses, '서울 평균보다 낮은 시설이 없습니다.')}
    </div>
  );
}

function HorizontalBars({ items }: { items: TypeMixItem[] }) {
  const top = items.slice(0, 6);
  const max = maxNumber(top.map((item) => item.count));
  return (
    <div className="grid gap-2">
      {top.map((item) => {
        const label = readableCategory(item.category) || item.housing_type || item.label || '-';
        return (
        <div key={`${item.category ?? item.housing_type ?? item.label}`} className="group relative grid grid-cols-[86px_1fr_44px] items-center gap-2 text-[12px]">
          <span className="truncate font-bold text-text-muted">{label}</span>
          <span className="h-2 overflow-hidden rounded-full bg-surface-alt">
            <span className="block h-full rounded-full bg-[var(--color-heatmap-4)]" style={{ width: `${clampPercent(item.count, max)}%` }} />
          </span>
          <b className="text-right text-text">{Math.round(item.ratio)}%</b>
          <span className="pointer-events-none absolute right-0 top-[calc(100%+6px)] z-10 hidden rounded-[6px] border border-border bg-surface px-2 py-1.5 text-[12px] font-bold leading-5 text-text shadow-lg group-hover:block">
            {label} · {item.count.toLocaleString()}건 · {item.ratio.toFixed(1)}%
          </span>
        </div>
        );
      })}
    </div>
  );
}

function safetyLabel(item: SafetyGradeItem) {
  if (item.label) return item.label;
  const map: Record<string, string> = {
    score_safety: '안전',
    score_transit: '교통',
    score_amenity: '편의',
    score_rent: '주거비',
    score_total: '종합',
  };
  return map[item.key] ?? item.key.replace('score_', '');
}

function formatSafetyGrade(value?: number | null, unit = '등급') {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '-';
  const formatted = Number.isInteger(value) ? value.toString() : value.toFixed(1);
  return `${formatted}${unit}`;
}

function normalizeSafetySeoulText(text: string) {
  return text
    .replace(/전체 구 평균/g, '서울 기준')
    .replace(/서울 평균 안전 점수/g, '서울 기준 안전 점수')
    .replace(/서울 평균 안전 지표/g, '서울 기준 안전 지표');
}

function SafetyRadarChart({ items }: { items: SafetyGradeItem[] }) {
  const data = items.filter((item) => typeof item.score === 'number').slice(0, 6);
  const [hoveredItem, setHoveredItem] = useState<SafetyGradeItem | null>(null);
  const size = 220;
  const center = size / 2;
  const maxRadius = 78;
  const levels = [0, 1, 2, 3, 4, 5];
  const angleFor = (index: number) => (-Math.PI / 2) + (index / data.length) * Math.PI * 2;
  const pointFor = (index: number, value: number) => {
    const angle = angleFor(index);
    const radius = maxRadius * Math.max(0, Math.min(1, value / 5));
    return {
      x: center + Math.cos(angle) * radius,
      y: center + Math.sin(angle) * radius,
    };
  };
  const safetyValue = (raw?: number | null, score?: number | null) => {
    if (typeof raw === 'number' && Number.isFinite(raw)) {
      return Math.max(0, Math.min(5, 6 - raw));
    }
    if (typeof score === 'number' && Number.isFinite(score)) {
      return Math.max(0, Math.min(5, score / 20));
    }
    return 0;
  };

  if (data.length < 3) {
    return (
      <div className="grid min-h-[190px] place-items-center rounded-[var(--map-control-radius)] border border-dashed border-border bg-surface-alt text-[13px] font-semibold text-text-muted">
        안전 점수 데이터가 부족합니다.
      </div>
    );
  }

  const polygon = data
    .map((item, index) => {
      const point = pointFor(index, safetyValue(item.raw_value, item.score));
      return `${point.x.toFixed(1)},${point.y.toFixed(1)}`;
    })
    .join(' ');
  const seoulPolygon = data
    .map((item, index) => {
      const point = pointFor(index, safetyValue(item.seoul_raw_value, item.seoul_score));
      return `${point.x.toFixed(1)},${point.y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <div className="relative grid min-h-[190px] place-items-center">
      <svg viewBox={`0 0 ${size} ${size}`} className="h-[210px] w-full max-w-[260px]" role="img" aria-label="안전 점수 레이더 차트">
        {levels.map((level) => {
          if (level === 0) {
            return <circle key={level} cx={center} cy={center} r="2" fill="var(--color-border)" />;
          }
          return (
            <polygon
              key={level}
              points={data.map((_, index) => {
                const point = pointFor(index, level);
                return `${point.x.toFixed(1)},${point.y.toFixed(1)}`;
              }).join(' ')}
              fill="none"
              stroke="var(--color-border)"
              strokeWidth="1"
            />
          );
        })}
        {data.map((_, index) => {
          const point = pointFor(index, 5);
          return <line key={index} x1={center} y1={center} x2={point.x} y2={point.y} stroke="var(--color-border)" strokeWidth="1" />;
        })}
        <polygon points={seoulPolygon} fill="rgba(107,114,128,0.12)" stroke="#9ca3af" strokeWidth="2" strokeDasharray="5 4" />
        <polygon points={polygon} fill="rgba(239,68,68,0.16)" stroke="var(--color-danger)" strokeWidth="3" />
        {data.map((item, index) => {
          const point = pointFor(index, safetyValue(item.raw_value, item.score));
          const seoulPoint = pointFor(index, safetyValue(item.seoul_raw_value, item.seoul_score));
          const labelPoint = pointFor(index, 5.9);
          return (
            <g
              key={item.key}
              onMouseEnter={() => setHoveredItem(item)}
              onMouseLeave={() => setHoveredItem(null)}
              onFocus={() => setHoveredItem(item)}
              onBlur={() => setHoveredItem(null)}
              tabIndex={0}
            >
              <circle cx={seoulPoint.x} cy={seoulPoint.y} r="3.5" fill="#9ca3af" />
              <circle cx={point.x} cy={point.y} r="4" fill="var(--color-danger)" />
              <circle cx={point.x} cy={point.y} r="12" fill="transparent" style={{ pointerEvents: 'all' }} />
              <text x={labelPoint.x} y={labelPoint.y} textAnchor="middle" dominantBaseline="middle" className="fill-text-muted text-[11px] font-bold" style={{ pointerEvents: 'all' }}>
                {safetyLabel(item)}
              </text>
            </g>
          );
        })}
      </svg>
      {hoveredItem ? (
        <div className="pointer-events-none absolute left-1/2 top-2 z-[3000] min-w-[170px] -translate-x-1/2 rounded-[6px] border border-border bg-[var(--surface-overlay-bg)] px-2 py-1.5 text-center text-[12px] font-bold leading-5 text-text shadow-lg backdrop-blur-md">
          {safetyLabel(hoveredItem)}<br />
          선택 지역 {formatSafetyGrade(hoveredItem.raw_value, hoveredItem.unit || '등급')}<br />
          <small className="font-semibold text-text-muted">서울 기준 {formatSafetyGrade(hoveredItem.seoul_raw_value, hoveredItem.unit || '등급')}</small>
        </div>
      ) : null}
      <div className="mt-[-8px] flex gap-3 text-[11px] font-bold text-text-muted">
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-[var(--color-danger)]" />선택 지역</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-[#9ca3af]" />서울 기준</span>
      </div>
    </div>
  );
}

function apiImageUrl(path: string, params: Record<string, string | number | undefined>) {
  const base = String(api.defaults.baseURL ?? '/api').replace(/\/$/, '');
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) query.set(key, String(value));
  });
  return `${base}${path}${path.includes('?') ? '&' : '?'}${query.toString()}`;
}

type Bbox = [number, number, number, number];
type WmsDisplay = {
  bbox: Bbox;
  width: number;
  height: number;
};
type DongFeature = Feature<Polygon | MultiPolygon, { adm_cd?: string; adm_cd2?: string; adong_code?: string; ldong_code?: string; code?: string; slug?: string; adm_nm?: string; name?: string }>;
const SAFETY_WMS_REFERENCE_HEIGHT = 300;

function boundsFromBbox(bbox: Bbox): LatLngBoundsExpression {
  return [[bbox[1], bbox[0]], [bbox[3], bbox[2]]];
}

function ringFromBbox(bbox?: Bbox | null): number[][] | null {
  if (!bbox || bbox.length !== 4) return null;
  const [west, south, east, north] = bbox;
  return [
    [west, south],
    [east, south],
    [east, north],
    [west, north],
    [west, south],
  ];
}

function featureCode(feature?: DongFeature | null): string {
  const p = feature?.properties;
  return p?.adm_cd2 ?? p?.adm_cd ?? p?.adong_code ?? p?.ldong_code ?? p?.code ?? p?.slug ?? '';
}

function selectedRings(feature?: DongFeature | null): number[][][] {
  if (!feature) return [];
  if (feature.geometry.type === 'Polygon') return [feature.geometry.coordinates[0]];
  return feature.geometry.coordinates.reduce<number[][][]>((acc, polygon) => {
    if (polygon[0]) acc.push(polygon[0]);
    return acc;
  }, []);
}

function ringPathForMap(ring: number[][], map: LeafletMap): string {
  return `${ring.map(([lng, lat], index) => {
    const point = map.latLngToContainerPoint([lat, lng]);
    return `${index === 0 ? 'M' : 'L'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`;
  }).join(' ')} Z`;
}

function regionMaskSvgPath(feature: DongFeature | null, fallbackBbox: Bbox | null | undefined, map: LeafletMap): { path: string; width: number; height: number } | null {
  const holes = selectedRings(feature);
  if (!holes.length) {
    const fallbackRing = ringFromBbox(fallbackBbox);
    if (fallbackRing) holes.push(fallbackRing);
  }
  if (!holes.length) return null;
  const size = map.getSize();
  const outer = `M0 0H${size.x}V${size.y}H0Z`;
  return {
    width: size.x,
    height: size.y,
    path: `${outer} ${holes.map((ring) => ringPathForMap(ring, map)).join(' ')}`,
  };
}

function regionBoundarySvgPath(feature: DongFeature | null, fallbackBbox: Bbox | null | undefined, map: LeafletMap): { path: string; width: number; height: number } | null {
  const rings = selectedRings(feature);
  if (!rings.length) {
    const fallbackRing = ringFromBbox(fallbackBbox);
    if (fallbackRing) rings.push(fallbackRing);
  }
  if (!rings.length) return null;
  const size = map.getSize();
  return {
    width: size.x,
    height: size.y,
    path: rings.map((ring) => ringPathForMap(ring, map)).join(' '),
  };
}

function SafetyWmsOverlay({
  path,
  regionBounds,
  selectedFeature,
  fallbackBbox,
  selectedKey,
}: {
  path: string;
  regionBounds: LatLngBoundsExpression;
  selectedFeature: DongFeature | null;
  fallbackBbox?: Bbox | null;
  selectedKey: string;
}) {
  const map = useMap();
  const [display, setDisplay] = useState<WmsDisplay | null>(null);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      map.invalidateSize();
      const bounds = L.latLngBounds(regionBounds as L.LatLngBoundsLiteral);
      const size = map.getSize();
      const center = bounds.getCenter();
      const crs = map.options.crs ?? L.CRS.EPSG3857;
      const north = crs.latLngToPoint(L.latLng(bounds.getNorth(), center.lng), 0);
      const south = crs.latLngToPoint(L.latLng(bounds.getSouth(), center.lng), 0);
      const yDistance = Math.abs(south.y - north.y);
      if (size.y > 0 && yDistance > 0) {
        const verticalZoom = Math.min(VWORLD_MAX_ZOOM, Math.log2(SAFETY_WMS_REFERENCE_HEIGHT / yDistance));
        map.setView(center, verticalZoom, { animate: false });
      } else {
        map.fitBounds(bounds, { animate: false, padding: [0, 0], maxZoom: VWORLD_MAX_ZOOM });
      }
      const nextSize = map.getSize();
      const visible = map.getBounds();
      setDisplay({
        bbox: [visible.getWest(), visible.getSouth(), visible.getEast(), visible.getNorth()],
        width: Math.max(1, Math.round(nextSize.x)),
        height: Math.max(1, Math.round(nextSize.y)),
      });
    }, 0);
    return () => window.clearTimeout(handle);
  }, [map, regionBounds]);

  const imageBounds = useMemo<LatLngBoundsExpression | null>(() => display ? boundsFromBbox(display.bbox) : null, [display]);
  const imageUrl = display ? apiImageUrl(path, { width: display.width, height: display.height, transparent: 'TRUE', bbox: display.bbox.join(',') }) : null;
  const maskSvg = useMemo(
    () => display ? regionMaskSvgPath(selectedFeature, fallbackBbox, map) : null,
    [display, fallbackBbox, map, selectedFeature],
  );
  const boundarySvg = useMemo(
    () => display ? regionBoundarySvgPath(selectedFeature, fallbackBbox, map) : null,
    [display, fallbackBbox, map, selectedFeature],
  );
  const maskKey = `safety-mask-${selectedKey}-${featureCode(selectedFeature) || fallbackBbox?.join(',') || 'none'}`;

  if (!imageBounds || !imageUrl) return null;

  return (
    <>
      <Pane name="safety-wms-pane" style={{ zIndex: 410 }}>
        <ImageOverlay url={imageUrl} bounds={imageBounds} opacity={0.78} />
      </Pane>
      {maskSvg ? (
        <svg
          key={maskKey}
          aria-hidden="true"
          viewBox={`0 0 ${maskSvg.width} ${maskSvg.height}`}
          preserveAspectRatio="none"
          style={{ position: 'absolute', inset: 0, zIndex: 650, width: '100%', height: '100%', pointerEvents: 'none' }}
        >
          <path d={maskSvg.path} fill="#6b7280" fillOpacity="0.55" fillRule="evenodd" />
        </svg>
      ) : null}
      {boundarySvg ? (
        <svg
          key={`safety-boundary-svg-${selectedKey}-${featureCode(selectedFeature) || fallbackBbox?.join(',') || 'none'}`}
          aria-hidden="true"
          viewBox={`0 0 ${boundarySvg.width} ${boundarySvg.height}`}
          preserveAspectRatio="none"
          style={{ position: 'absolute', inset: 0, zIndex: 720, width: '100%', height: '100%', pointerEvents: 'none' }}
        >
          <path d={boundarySvg.path} fill="none" stroke="#111827" strokeWidth="2.4" strokeLinejoin="round" />
        </svg>
      ) : null}
      <Pane name="safety-boundary-pane" style={{ zIndex: 700, pointerEvents: 'none' }}>
        {selectedFeature ? <GeoJSON key={`safety-boundary-${selectedKey}-${featureCode(selectedFeature)}`} data={selectedFeature} style={{ color: '#111827', weight: 2, fillColor: 'transparent', fillOpacity: 0 }} interactive={false} /> : null}
      </Pane>
    </>
  );
}

function SafetyWmsMap({ regionLevel, slug, meta }: { regionLevel: RegionLevel; slug: string | null; meta?: SafetyWmsLayerResponse }) {
  const { theme } = useTheme();
  const adongGeo = useAdongGeoJson();
  const ldongGeo = useLdongGeoJson();
  const bbox = meta?.region?.bbox;
  const regionBounds = useMemo<LatLngBoundsExpression | null>(() => {
    if (!bbox || bbox.length !== 4) return null;
    return boundsFromBbox(bbox);
  }, [bbox]);
  const geojson = regionLevel === 'adong' ? adongGeo.data : ldongGeo.data;
  const selectedFeature = useMemo<DongFeature | null>(() => {
    const code = meta?.region?.code ?? slug ?? null;
    const name = typeof meta?.region?.name === 'string' ? meta.region.name : null;
    if (!geojson || !code) return null;
    return (geojson.features.find((feature) => {
      const typed = feature as DongFeature;
      const p = typed.properties;
      return featureCode(typed) === code || p?.adm_cd === code || p?.adm_cd2 === code || p?.adm_nm === name || p?.name === name;
    }) as DongFeature | undefined) ?? null;
  }, [geojson, meta?.region?.code, meta?.region?.name, slug]);
  const viewportBounds = useMemo<LatLngBoundsExpression | null>(() => {
    if (!selectedFeature) return regionBounds;
    const bounds = L.geoJSON(selectedFeature).getBounds();
    return bounds.isValid() ? bounds : regionBounds;
  }, [regionBounds, selectedFeature]);
  const path = slug ? endpoint('safety/crime-zone', regionLevel, slug) : null;
  const selectedKey = `${regionLevel}-${meta?.region?.code ?? slug ?? 'none'}`;
  const maxZoom = getVWorldMaxNativeZoom(theme);

  if (!viewportBounds || !path) {
    return (
      <div className="grid h-full min-h-[340px] place-items-center rounded-[var(--map-control-radius)] border border-dashed border-border bg-surface-alt text-[13px] font-semibold text-text-muted">
        안전 지도 영역을 불러올 수 없습니다.
      </div>
    );
  }

  return (
    <div className="group relative h-full min-h-[340px] overflow-hidden rounded-[var(--map-control-radius)] border border-border bg-surface-alt">
      <div className="pointer-events-none absolute right-3 top-3 z-[1800] hidden w-[270px] rounded-[6px] border border-border bg-surface p-3 text-[12px] font-semibold leading-5 text-text-muted shadow-lg group-hover:block">
        범죄주의구간은 생활안전지도에서 제공하는 범죄 관련 주의 레이어입니다. 붉은색이 강할수록 주의가 필요한 구간으로 참고하세요.
      </div>
      <MapContainer
        bounds={viewportBounds}
        maxZoom={maxZoom}
        zoomControl={false}
        dragging={false}
        scrollWheelZoom={false}
        doubleClickZoom={false}
        boxZoom={false}
        keyboard={false}
        touchZoom={false}
        attributionControl={false}
        style={{ width: '100%', height: '100%', minHeight: 340 }}
      >
        <TileLayer
          url={getVWorldTileUrl(theme)}
          maxZoom={maxZoom}
          maxNativeZoom={maxZoom}
        />
        <SafetyWmsOverlay path={path} regionBounds={viewportBounds} selectedFeature={selectedFeature} fallbackBbox={bbox} selectedKey={selectedKey} />
      </MapContainer>
    </div>
  );
}

export default function DashboardSections({ region, regionLevel, slug }: DashboardSectionsProps) {
  const basePath = slug ? `${regionLevel}:${slug}` : null;
  const dashboardCache = useDashboardData<DashboardCacheResponse>('dashboard-cache', slug ? endpoint('cache', regionLevel, slug) : null);
  const rentSummary = { data: dashboardCache.data?.rent_summary };
  const transitOverview = { data: dashboardCache.data?.transit_summary?.overview };
  const congestion = { data: dashboardCache.data?.transit_summary?.congestion };
  const infraOverview = { data: dashboardCache.data?.infra_summary?.overview };
  const infraMix = { data: dashboardCache.data?.infra_summary?.category_mix };
  const safetyOverview = { data: dashboardCache.data?.safety_summary?.overview };
  const safetyGrades = { data: dashboardCache.data?.safety_summary?.grades };
  const safetyWmsMeta = { data: dashboardCache.data?.safety_summary?.wms };

  const rentOverview = rentSummary.data?.overview;
  const rentVolume = rentSummary.data?.volume_trend;
  const rentTrend = rentSummary.data?.rent_trend;
  const rentMix = rentSummary.data?.housing_type_mix;
  const rentMetrics = rentOverview?.metrics ?? [];
  const transitMetrics = transitOverview.data?.metrics ?? [];
  const infraMetrics = infraOverview.data?.metrics ?? [];
  const safetyMetrics = safetyOverview.data?.metrics ?? [];
  const rentDealCount = Number(pickMetric(rentMetrics, 'deal_count_6m')?.value ?? 0);
  const hasRentDeals = rentDealCount > 0 || (rentVolume?.items ?? []).some((item) => Number(item.count ?? 0) > 0);

  const regionName = region?.name ?? '선택 지역';
  const primaryHousing = rentMix?.items?.[0]?.housing_type ?? '주요 유형';
  const safetyScore = region?.score_safety ?? pickMetric(safetyMetrics, 'safety_score')?.value;
  const conversionRate = rentOverview?.basis?.conversion_rate;
  const conversionText = typeof conversionRate === 'number'
    ? `전월세전환율 ${conversionRate.toFixed(2)}% 적용 · 한국부동산원 서울 최근 평균 기준`
    : '전월세전환율 적용 · 한국부동산원 서울 최근 평균 기준';
  const rentInfo = `${conversionText}. 보증금은 이 전환율로 월세 환산 후 비교하며, 가격 평가는 선택 동의 ㎡당 환산월세를 서울 기준과 비교한 참고값입니다.`;
  const transitInfo = '지하철역과 버스정류장은 지역 면적당 시설 밀도를 서울 평균과 비교합니다. 혼잡도는 버스/지하철과 평일/주말을 분리해 표시합니다.';
  const infraInfo = '생활 인프라는 면적당 시설 밀도와 녹지율을 서울 평균과 비교하고, 식생활·문화·학습·의료 그룹의 밀도와 시설 구성을 함께 봅니다.';
  const safetyInfo = '지역 안전 점수는 자치구 단위로 산출되는 안전등급을 기반으로 만들어졌습니다. 범죄주의구간은 지도 레이어에서 실제 위치를 확인해야 합니다.';
  const safetySummary = normalizeSafetySeoulText(
    safetyOverview.data?.summary ?? '서울 기준 안전 지표와 생활안전지도 범죄주의구간 레이어를 함께 참고합니다.',
  );
  const safetyQuicktakes = safetyOverview.data?.quicktakes?.map((item) => ({
    ...item,
    label: normalizeSafetySeoulText(item.label),
  }));

  return (
    <div className="mt-5 grid gap-4" data-region={basePath ?? ''}>
      {hasRentDeals ? <section className="rounded-card border border-border bg-surface p-5 shadow-sm">
        <SectionHeader
          kicker="거래 시세 요약"
          title={rentOverview?.headline ?? `${primaryHousing} 중심의 최근 임대 구조`}
          summary={rentOverview?.summary ?? `${regionName}의 최근 거래량, 환산월세, 면적, 매물 유형을 함께 봅니다.`}
          info={rentInfo}
        >
          <SummaryCluster quicktakes={rentOverview?.quicktakes} />
        </SectionHeader>

        <MetricGrid items={[
          { label: '㎡당 환산월세', value: metricValue(pickMetric(rentMetrics, 'converted_rent_per_area')), badge: pickMetric(rentMetrics, 'converted_rent_per_area')?.badge ?? '면적', tone: pickMetric(rentMetrics, 'converted_rent_per_area')?.tone, note: '면적까지 반영한 비용감' },
          { label: '중위 환산월세', value: metricValue(pickMetric(rentMetrics, 'median_converted_monthly_rent')), badge: pickMetric(rentMetrics, 'median_converted_monthly_rent')?.badge ?? '비용', tone: pickMetric(rentMetrics, 'median_converted_monthly_rent')?.tone, note: '보증금을 월세로 환산한 비교값' },
          { label: '중위 전용면적', value: metricValue(pickMetric(rentMetrics, 'median_area')), badge: pickMetric(rentMetrics, 'median_area')?.badge ?? '크기', tone: pickMetric(rentMetrics, 'median_area')?.tone, note: '최근 거래 매물의 중간 면적' },
          { label: '최근 6개월 거래', value: metricValue(pickMetric(rentMetrics, 'deal_count_6m')), badge: pickMetric(rentMetrics, 'deal_count_6m')?.badge ?? '거래', tone: pickMetric(rentMetrics, 'deal_count_6m')?.tone, note: pickMetric(rentMetrics, 'deal_count_6m')?.description ?? '최근 거래 건수' },
        ]} />

        <div className="mt-4 grid grid-cols-4 gap-3">
          <Card title="월별 거래량" hint="최근 6개월">
            <BarChart items={rentVolume?.items ?? []} />
          </Card>
          <Card title="㎡당 환산월세 추이" hint="유형별 · 만원/㎡" className="col-span-2">
            <MultiSeriesLineChart series={rentTrendSeries(rentTrend?.series)} emptyText="유형별 추이 데이터가 없습니다." unit="만원/㎡" />
          </Card>
          <Card title="매물 종류" hint="비중">
            <HorizontalBars items={rentMix?.items ?? []} />
          </Card>
        </div>
      </section> : null}

      <section className="rounded-card border border-border bg-surface p-5 shadow-sm">
        <SectionHeader
          kicker="교통 접근성"
          title={transitOverview.data?.headline ?? '교통시설 밀도와 혼잡도를 함께 봅니다'}
          summary={transitOverview.data?.summary ?? `${regionName}의 지하철역·버스정류장 밀도와 시간대 혼잡도를 서울 기준으로 봅니다.`}
          info={transitInfo}
        >
          <SummaryCluster quicktakes={transitOverview.data?.quicktakes} />
        </SectionHeader>
        <div className="mt-4 grid grid-cols-[0.48fr_2.52fr] grid-rows-[minmax(176px,1fr)_minmax(176px,1fr)] gap-3">
          <div className="col-start-1 row-start-1 grid min-h-0 gap-2">
            <MetricGrid
              className="grid h-full grid-cols-1 grid-rows-2 gap-2"
              itemClassName="!min-h-0 p-3"
              items={[
                { label: '지하철역 밀도', value: metricValue(pickMetric(transitMetrics, 'subway_station_density')), badge: pickMetric(transitMetrics, 'subway_station_density')?.badge ?? '보통', tone: pickMetric(transitMetrics, 'subway_station_density')?.tone, note: pickMetric(transitMetrics, 'subway_station_density')?.description ?? '서울 평균 대비' },
                { label: '버스정류장 밀도', value: metricValue(pickMetric(transitMetrics, 'bus_stop_density')), badge: pickMetric(transitMetrics, 'bus_stop_density')?.badge ?? '보통', tone: pickMetric(transitMetrics, 'bus_stop_density')?.tone, note: pickMetric(transitMetrics, 'bus_stop_density')?.description ?? '서울 평균 대비' },
              ]}
            />
          </div>
          <div className="col-start-1 row-start-2 min-h-0">
            <TransitStationList stations={transitOverview.data?.station_names} stationItems={transitOverview.data?.station_items} />
          </div>
          <div className="col-start-2 row-start-1 min-h-0">
            <Card
              title="지하철 혼잡도 흐름"
              hint="평일/주말 · 공통축 04:00~익일 03:00"
              info="1km 이내 역 혼잡도를 거리 가중 평균으로 계산합니다. 가중치 = 1 / (거리 + 200m)"
              className="h-full !min-h-[176px]"
            >
              <CongestionLineChart series={congestion.data?.series} mode="subway" />
            </Card>
          </div>
          <div className="col-start-2 row-start-2 min-h-0">
            <Card title="버스 혼잡도 흐름" hint="평일/주말 · 04:00~익일 03:00" className="h-full !min-h-[176px]">
              <CongestionLineChart series={congestion.data?.series} mode="bus" />
            </Card>
          </div>
        </div>
      </section>

      <section className="rounded-card border border-border bg-surface p-5 shadow-sm">
        <SectionHeader
          kicker="생활 인프라"
          title={infraOverview.data?.headline ?? `면적당 시설은 ${metricValue(pickMetric(infraMetrics, 'amenity_density'))} 수준입니다`}
          summary={infraOverview.data?.summary ?? '식생활, 문화, 학습, 의료 시설을 서울 평균과 함께 봅니다.'}
          info={infraInfo}
        >
          <SummaryCluster quicktakes={infraOverview.data?.quicktakes} />
        </SectionHeader>
        <MetricGrid items={[
          { label: '면적당 시설', value: metricValue(pickMetric(infraMetrics, 'amenity_density')), badge: pickMetric(infraMetrics, 'amenity_density')?.badge ?? '시설', tone: pickMetric(infraMetrics, 'amenity_density')?.tone, note: pickMetric(infraMetrics, 'amenity_density')?.description ?? '서울 평균 대비' },
          { label: '녹지율', value: metricValue(pickMetric(infraMetrics, 'green_ratio')), badge: pickMetric(infraMetrics, 'green_ratio')?.badge ?? '녹지', tone: pickMetric(infraMetrics, 'green_ratio')?.tone, note: pickMetric(infraMetrics, 'green_ratio')?.description ?? '서울 평균 대비' },
          { label: '식생활 밀도', value: metricValue(pickMetric(infraMetrics, 'food_density')), badge: pickMetric(infraMetrics, 'food_density')?.badge ?? '식생활', tone: pickMetric(infraMetrics, 'food_density')?.tone, note: pickMetric(infraMetrics, 'food_density')?.description ?? '서울 평균 대비' },
          { label: '의료 밀도', value: metricValue(pickMetric(infraMetrics, 'medical_density')), badge: pickMetric(infraMetrics, 'medical_density')?.badge ?? '의료', tone: pickMetric(infraMetrics, 'medical_density')?.tone, note: pickMetric(infraMetrics, 'medical_density')?.description ?? '서울 평균 대비' },
        ]} />
        <div className="mt-4 grid grid-cols-[1fr_1.25fr_1fr] gap-3">
          <Card title="그룹별 밀도" hint="서울 평균 대비" className="!min-h-[236px]">
            <InfraDensityDotPlot items={infraMix.data?.items ?? []} />
          </Card>
          <Card title="시설 유형 구성" hint="면적 비례">
            <InfraTreemap items={infraMix.data?.items ?? []} />
          </Card>
          <Card title="강점·부족 시설" hint="서울 평균 대비">
            <InfraDivergingBars items={infraMix.data?.items ?? []} />
          </Card>
        </div>
      </section>

      <section className="rounded-card border border-border bg-surface p-5 shadow-sm">
        <SectionHeader
          kicker="안전"
          title={safetyOverview.data?.headline ?? `안전 점수는 ${typeof safetyScore === 'number' ? Math.round(safetyScore) : '-'}점입니다`}
          summary={safetySummary}
          info={safetyInfo}
        >
          <SummaryCluster quicktakes={safetyQuicktakes} />
        </SectionHeader>
        <div className="mt-4 grid grid-cols-[0.82fr_1.18fr] gap-3">
          <div className="grid gap-3">
            <MetricGrid
              className="grid grid-cols-2 gap-3"
              items={[
                { label: '지역 안전 점수', value: metricValue(pickMetric(safetyMetrics, 'safety_score'), typeof safetyScore === 'number' ? Math.round(safetyScore).toString() : '-'), badge: pickMetric(safetyMetrics, 'safety_score')?.badge ?? '안전', tone: pickMetric(safetyMetrics, 'safety_score')?.tone, note: pickMetric(safetyMetrics, 'safety_score')?.description ?? '지역안전등급 평균 환산 점수' },
                { label: '서울 기준 안전 점수', value: metricValue(pickMetric(safetyMetrics, 'seoul_safety_score')), badge: '서울', tone: pickMetric(safetyMetrics, 'seoul_safety_score')?.tone, note: '서울 단위 안전등급 저장값 기준' },
              ]}
            />
            <Card
              title="안전등급 구성"
              info="레이더 면적이 클수록 안전 수준이 높습니다. 원자료는 1등급이 가장 안전하고 5등급이 가장 낮습니다. 차트는 등급을 보기 쉽게 변환해 표시하며, 회색 영역은 서울 단위 저장값입니다."
              className="!min-h-[252px]"
            >
              <SafetyRadarChart items={safetyGrades.data?.items ?? []} />
            </Card>
          </div>
          <Card title="안전 지도 레이어" className="!min-h-[380px]">
            <SafetyWmsMap regionLevel={regionLevel} slug={slug} meta={safetyWmsMeta.data} />
          </Card>
        </div>
      </section>
    </div>
  );
}
