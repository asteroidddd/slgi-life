import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useMap, useMapEvents } from 'react-leaflet';

import HeatMap from '@/components/Map/HeatMap';
import type { ScoreLayerKey } from '@/components/Map/HeatMap';
import TransactionPinLayer, { jibunKeyOf } from '@/components/Map/TransactionPinLayer';
import type { MapState } from '@/components/Map/TransactionPinLayer';
import { useAiPanel } from '@/contexts/AiPanelContext';
import { useAuth } from '@/contexts/AuthContext';
import { useAdongMatchCounts } from '@/hooks/useAdongMatchCounts';
import { useAdongScores } from '@/hooks/useAdongs';
import {
  DEFAULT_STUDIO_MATCH_FILTERS,
  useStudioMatchFilters,
} from '@/hooks/useStudioMatchFilters';
import { useTransactions } from '@/hooks/useTransactions';
import { getMapSearch } from '@/lib/api';
import { DEFAULT_WEIGHTS } from '@/types/api';
import type {
  AdongScore,
  ExploreDealType,
  ExplorePeriod,
  MapSearchItem,
  MatchFilters,
  RentDealPin,
  TransactionDealTypeFilter,
  TransactionFilters,
} from '@/types/api';

import 'leaflet/dist/leaflet.css';

type MapMode = 'plain' | 'heatmap' | 'realestate' | 'facility';
type RegionLevel = 'adong' | 'ldong';
type HeatLayer = ScoreLayerKey | 'safety';
type FacilityKey =
  | 'university'
  | 'park'
  | 'subway'
  | 'bus'
  | 'hospital'
  | 'pharmacy'
  | 'restaurant'
  | 'cafe'
  | 'mart'
  | 'library';

type SelectedPopup =
  | { type: 'adong'; adong: AdongScore }
  | { type: 'deal'; key: string; pins: RentDealPin[] }
  | { type: 'facility'; title: string; description: string }
  | { type: 'search'; item: MapSearchItem }
  | null;

const HEAT_LAYERS: Array<{ key: HeatLayer; label: string }> = [
  { key: 'composite', label: '종합 점수' },
  { key: 'rent', label: '부동산 점수' },
  { key: 'transit', label: '교통 점수' },
  { key: 'amenity', label: '편의시설 점수' },
  { key: 'safety', label: '안전 지수' },
];

const HEAT_LAYER_DESCRIPTIONS: Record<HeatLayer, string> = {
  composite: '기본 가중치 33/33/34로 부동산·편의시설·교통 점수를 합산한 값입니다.',
  rent: '최근 365일 실거래의 (월세 + 보증금×0.005) / 면적(m²)을 계산하고, 상하위 5%를 줄인 평균을 사용합니다. 값이 낮을수록 높은 점수입니다.',
  transit: '가장 가까운 지하철역 거리 점수 60%와 면적당 버스정류장 밀도 점수 40%를 합산합니다. 지하철 거리는 1km를 기준으로 멀수록 낮아집니다.',
  amenity: '면적당 생활시설 밀도 60.9%, 의료시설 밀도 10.8%, 공원 면적 비율 28.3%를 합산합니다. 생활/의료 밀도는 로그 정규화합니다.',
  safety: '현재 히트맵 연결 전입니다. 추후 구 단위 안전 지표를 연결할 예정입니다.',
};

const DEAL_TYPE_LABELS: Record<ExploreDealType, string> = {
  villa: '연립다세대',
  dagagu: '다가구',
  danok: '단독',
  officetel: '오피스텔',
  apt: '아파트',
};

const PERIOD_LABELS: Record<ExplorePeriod, string> = {
  '3m': '최근 3개월',
  '6m': '최근 6개월',
  '12m': '최근 1년',
  '24m': '최근 2년',
  all: '전체 기간',
};

const FACILITY_LABELS: Record<FacilityKey, string> = {
  university: '대학',
  park: '공원',
  subway: '지하철역',
  bus: '버스정류장',
  hospital: '병원',
  pharmacy: '약국',
  restaurant: '음식점',
  cafe: '카페',
  mart: '편의점/마트',
  library: '도서관',
};

const RANGE_ALL = {
  deposit: { min: 0, max: 999_999 },
  monthly: { min: 0, max: 9_999 },
  converted: { min: 0, max: 9_999 },
  area: { min: 0, max: 10_000 },
};

function formatRangeLabel(label: string, min: number, max: number, allMax: number, unit = '') {
  if (min <= 0 && max >= allMax) return `${label} 전체`;
  return `${label} ${min.toLocaleString()}-${max.toLocaleString()}${unit}`;
}

function periodToFrom(period: ExplorePeriod, today: Date = new Date()): string | null {
  if (period === 'all') return null;
  const days = period === '3m' ? 90 : period === '6m' ? 180 : period === '12m' ? 365 : 730;
  const t = new Date(today);
  t.setDate(t.getDate() - days);
  const y = t.getFullYear();
  const m = String(t.getMonth() + 1).padStart(2, '0');
  const d = String(t.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function matchFiltersToTxFilters(f: MatchFilters): TransactionFilters {
  const dealType: TransactionDealTypeFilter =
    f.deal_types.length === 1 ? (f.deal_types[0] as TransactionDealTypeFilter) : 'all';
  return { deal_type: dealType, from: periodToFrom(f.period), to: null };
}

function applyClientPinFilter(pins: RentDealPin[], f: MatchFilters): RentDealPin[] {
  return pins.filter((p) => {
    if (!f.deal_types.includes(p.deal_type)) return false;
    if (p.deposit < f.deposit_min || p.deposit > f.deposit_max) return false;
    if (p.monthly_rent < f.monthly_min || p.monthly_rent > f.monthly_max) return false;
    const converted = p.converted_rent ?? p.monthly_rent;
    if (converted < f.converted_min || converted > f.converted_max) return false;
    if (p.area_m2 < f.area_min || p.area_m2 > f.area_max) return false;
    return true;
  });
}

function formatDealTypes(types: ExploreDealType[]) {
  if (types.length >= 5) return '전체 유형';
  if (types.length === DEFAULT_STUDIO_MATCH_FILTERS.deal_types.length &&
      types.every((t) => DEFAULT_STUDIO_MATCH_FILTERS.deal_types.includes(t))) {
    return '자취 기본 유형';
  }
  return types.map((t) => DEAL_TYPE_LABELS[t]).join(', ');
}


function FilterButton({
  children,
  active,
  onClick,
  className = '',
}: {
  children: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-9 w-full rounded-[var(--map-control-radius)] border px-3 text-left text-[13px] font-semibold shadow-sm transition ${
        active
          ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]'
          : 'border-border bg-white/95 text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
      } ${className}`}
    >
      {children}
    </button>
  );
}



function ResetButton({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="h-9 w-full rounded-[var(--map-control-radius)] border border-border bg-surface-alt px-3 text-[13px] font-semibold text-text-muted shadow-sm transition hover:bg-border/60 hover:text-text"
    >
      {children}
    </button>
  );
}

function SegmentButton({
  children,
  active,
  onClick,
}: {
  children: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-8 rounded-[var(--map-control-radius)] px-3 text-[13px] font-semibold transition ${
        active ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm' : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
      }`}
    >
      {children}
    </button>
  );
}

function ModeGuide({
  title,
  children,
  className = '',
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <aside
      className={`w-[var(--map-control-width)] rounded-card border border-border/70 bg-[var(--map-guide-bg)] px-3 py-2.5 text-left shadow-lg backdrop-blur ${className}`}
      aria-label={`${title} 안내`}
    >
      <strong className="block text-[13px] font-semibold text-text">{title}</strong>
      <p className="m-0 mt-1 whitespace-normal break-keep text-[12px] leading-[1.45] text-text-muted">{children}</p>
    </aside>
  );
}

function DropdownButton({
  id,
  label,
  active,
  open,
  onToggle,
  onClose,
  children,
  width = 'w-[224px]',
}: {
  id: string;
  label: string;
  active?: boolean;
  open: boolean;
  onToggle: (id: string) => void;
  onClose?: () => void;
  children: React.ReactNode;
  width?: string;
}) {
  return (
    <div className={`relative ${width}`}>
      <button
        type="button"
        onClick={() => onToggle(id)}
        className={`flex h-9 w-full items-center justify-between rounded-[var(--map-control-radius)] border px-3 text-[13px] font-semibold shadow-sm transition ${
          active ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'border-border bg-white/95 text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
        }`}
        aria-expanded={open}
      >
        <span className="truncate">{label}</span>
        <span className="ml-2 text-[14px] leading-none" aria-hidden="true">▾</span>
      </button>
      {open ? (
        <div className="absolute left-[calc(100%+8px)] top-0 z-[600] w-[300px] rounded-[8px] border border-border bg-white p-3 shadow-xl">
          {onClose ? (
            <button type="button" onClick={onClose} className="absolute right-2 top-2 h-7 w-7 rounded-[6px] bg-surface-alt text-[16px] text-text-muted">×</button>
          ) : null}
          {children}
        </div>
      ) : null}
    </div>
  );
}

function ChoiceList({
  items,
  selected,
  onSelect,
}: {
  items: Array<{ value: string; label: string }>;
  selected: string;
  onSelect: (value: string) => void;
}) {
  return (
    <div className="grid gap-1">
      {items.map((item) => (
        <button
          key={item.value}
          type="button"
          onClick={() => onSelect(item.value)}
          className={`h-8 rounded-[6px] px-2 text-left text-[13px] font-medium ${
            selected === item.value ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function RangePanel({
  title,
  unit,
  min,
  max,
  onChange,
  presets,
}: {
  title: string;
  unit: string;
  min: number;
  max: number;
  onChange: (min: number, max: number) => void;
  presets: Array<{ label: string; min: number; max: number }>;
}) {
  return (
    <div className="grid gap-3">
      <h3 className="m-0 text-[14px] font-semibold text-text">{title}</h3>
      <div className="flex items-end gap-2">
        <label className="min-w-0 flex-1 grid gap-1 text-[12px] font-semibold text-text-muted">
          최소 {unit}
          <input
            type="number"
            value={min}
            onChange={(e) => onChange(Number(e.target.value), max)}
            className="h-8 w-full min-w-0 rounded-[6px] border border-border bg-surface-alt px-2 text-[13px] text-text"
          />
        </label>
        <label className="min-w-0 flex-1 grid gap-1 text-[12px] font-semibold text-text-muted">
          최대 {unit}
          <input
            type="number"
            value={max}
            onChange={(e) => onChange(min, Number(e.target.value))}
            className="h-8 w-full min-w-0 rounded-[6px] border border-border bg-surface-alt px-2 text-[13px] text-text"
          />
        </label>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {presets.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => onChange(p.min, p.max)}
            className="h-8 rounded-[6px] bg-surface-alt px-2 text-[12px] font-semibold text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]"
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function MapPopup({ popup, onClose, heatLayer, ranks, rankTotal }: { popup: SelectedPopup; onClose: () => void; heatLayer: HeatLayer; ranks: ScoreRanks; rankTotal: number }) {
  if (!popup) return null;
  if (popup.type === 'adong') {
    const { adong } = popup;
    return (
      <article className="absolute left-1/2 top-1/2 z-[550] w-[360px] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-[8px] border border-border bg-white shadow-xl">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <p className="m-0 text-[12px] font-semibold text-text-muted">{adong.gu}</p>
            <h2 className="m-0 text-[20px] font-semibold text-text">{adong.name}</h2>
          </div>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
        </header>
        <div className="grid gap-3 p-4">
          <div className="grid grid-cols-3 gap-2">
            <Metric label="종합" value={adong.score} rank={ranks.composite[adong.code]} rankTotal={rankTotal} active={heatLayer === 'composite'} className="col-span-3" />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <Metric label="부동산" value={adong.score_rent} rank={ranks.rent[adong.code]} rankTotal={rankTotal} active={heatLayer === 'rent'} />
            <Metric label="교통" value={adong.score_transit} rank={ranks.transit[adong.code]} rankTotal={rankTotal} active={heatLayer === 'transit'} />
            <Metric label="편의시설" value={adong.score_amenity} rank={ranks.amenity[adong.code]} rankTotal={rankTotal} active={heatLayer === 'amenity'} />
          </div>
        </div>
      </article>
    );
  }
  if (popup.type === 'deal') {
    const first = popup.pins[0];
    const address = [first.gu, first.dong_name, first.jibun].filter(Boolean).join(' ') || '주소 정보 없음';
    const deals = [...popup.pins].sort((a, b) => b.date.localeCompare(a.date));
    return (
      <article className="absolute left-1/2 top-1/2 z-[550] w-[380px] -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-white p-4 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="m-0 text-[12px] font-semibold text-text-muted">주소</p>
            <h2 className="m-0 text-[18px] font-semibold text-text">{address}</h2>
            <p className="mt-1 text-[12px] font-semibold text-text-subtle">{deals.length > 1 ? `${deals.length}건 거래` : deals[0]?.date}</p>
          </div>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
        </div>
        <div className="mt-3 max-h-[260px] overflow-y-auto pr-1">
          {deals.map((deal) => (
            <div key={deal.id} className="mb-2 rounded-card border border-border bg-surface-alt p-3 last:mb-0">
              <p className="m-0 text-[12px] font-semibold text-text-muted">{deal.date}</p>
              <div className="mt-2 grid grid-cols-3 gap-2">
                <Metric label="보증금" value={deal.deposit} suffix="만" />
                <Metric label="월세" value={deal.monthly_rent} suffix="만" />
                <Metric label="면적" value={Math.round(deal.area_m2)} suffix="m²" />
              </div>
            </div>
          ))}
        </div>
      </article>
    );
  }
  if (popup.type === 'search') {
    return (
      <article className="absolute left-1/2 top-1/2 z-[550] w-[320px] -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-white p-4 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="m-0 text-[12px] font-semibold text-text-muted">{popup.item.label}</p>
            <h2 className="m-0 text-[18px] font-semibold text-text">{popup.item.name}</h2>
            {popup.item.address ? <p className="mt-2 text-[13px] leading-5 text-text-muted">{popup.item.address}</p> : null}
          </div>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
        </div>
      </article>
    );
  }
  return (
    <article className="absolute left-1/2 top-1/2 z-[550] w-[320px] -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-white p-4 shadow-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="m-0 text-[18px] font-semibold text-text">{popup.title}</h2>
          <p className="mt-2 text-[13px] leading-5 text-text-muted">{popup.description}</p>
        </div>
        <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
      </div>
    </article>
  );
}

function Metric({ label, value, suffix = '', active = false, rank, rankTotal, className = '' }: { label: string; value: number; suffix?: string; active?: boolean; rank?: number; rankTotal?: number; className?: string }) {
  return (
    <div className={`rounded-card border p-3 ${active ? 'border-[var(--color-heatmap-4)] bg-[var(--color-heatmap-1)]' : 'border-border bg-surface-alt'} ${className}`}>
      <p className="m-0 text-[12px] font-semibold text-text-muted">{label}</p>
      <strong className="mt-1 block text-[20px] text-text">{Number.isFinite(value) ? Math.round(value) : '-'}{suffix}</strong>
      {rank && rankTotal ? <span className="mt-1 block text-[11px] font-semibold text-text-subtle">순위 {rank}/{rankTotal}</span> : null}
    </div>
  );
}

type ScoreRanks = Record<'composite' | 'rent' | 'transit' | 'amenity', Record<string, number>>;

function buildScoreRanks(adongs: AdongScore[]): ScoreRanks {
  const rankBy = (pick: (d: AdongScore) => number) => {
    const result: Record<string, number> = {};
    [...adongs]
      .sort((a, b) => pick(b) - pick(a))
      .forEach((d, index) => {
        result[d.code] = index + 1;
      });
    return result;
  };
  return {
    composite: rankBy((d) => d.score),
    rent: rankBy((d) => d.score_rent),
    transit: rankBy((d) => d.score_transit),
    amenity: rankBy((d) => d.score_amenity),
  };
}

export default function MainMap() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const { open: openAiPanel } = useAiPanel();
  const [regionLevel, setRegionLevel] = useState<RegionLevel>('adong');
  const [mapMode, setMapMode] = useState<MapMode>(() => {
    const mode = searchParams.get('mode');
    return mode === 'plain' || mode === 'heatmap' || mode === 'realestate' || mode === 'facility' ? mode : 'heatmap';
  });
  const [heatLayer, setHeatLayer] = useState<HeatLayer>('composite');
  const [facilityKeys, setFacilityKeys] = useState<Set<FacilityKey>>(
    () => new Set(['university', 'park', 'subway', 'bus']),
  );
  const [mapState, setMapState] = useState<MapState | null>(null);
  const [popup, setPopup] = useState<SelectedPopup>(null);
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState<MapSearchItem[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedSearchItem, setSelectedSearchItem] = useState<MapSearchItem | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [routeTransition, setRouteTransition] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [locateRequest, setLocateRequest] = useState(0);
  const toastTimer = useRef<number | null>(null);

  const { filters, patch, reset } = useStudioMatchFilters();
  const { data: scoresData = [], isLoading: scoresLoading, isError: scoresError } = useAdongScores(DEFAULT_WEIGHTS);
  const matchQuery = useAdongMatchCounts(filters, mapMode === 'realestate');
  const matchCounts = matchQuery.data?.adongs ?? [];

  const txFilters = useMemo(() => matchFiltersToTxFilters(filters), [filters]);
  const txQuery = useTransactions({ bbox: mapState?.bbox ?? null, zoom: mapState?.zoom ?? 0, filters: txFilters });
  const filteredPins = useMemo(() => {
    if (!txQuery.data) return [];
    return applyClientPinFilter(txQuery.data.items, filters);
  }, [txQuery.data, filters]);

  const ranks = useMemo(() => buildScoreRanks(scoresData), [scoresData]);

  const selectedJibun = popup?.type === 'deal' ? popup.key : null;
  const heatmapActiveLayer: ScoreLayerKey = heatLayer === 'safety' ? 'composite' : heatLayer;
  const heatmapMode = 'score';
  const heatmapVisible = mapMode === 'heatmap';
  const showRealEstatePins = mapMode === 'realestate';

  useEffect(() => {
    const q = searchText.trim();
    if (q.length < 2) {
      setSearchResults([]);
      setSearchLoading(false);
      return;
    }
    let cancelled = false;
    setSearchLoading(true);
    const timer = window.setTimeout(() => {
      getMapSearch(q)
        .then((data) => { if (!cancelled) setSearchResults(data.items); })
        .catch(() => { if (!cancelled) setSearchResults([]); })
        .finally(() => { if (!cancelled) setSearchLoading(false); });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [searchText]);

  const flash = (message: string) => {
    setToast(message);
    if (toastTimer.current != null) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => {
      setToast(null);
      toastTimer.current = null;
    }, 2200);
  };

  useEffect(() => () => {
    if (toastTimer.current != null) window.clearTimeout(toastTimer.current);
  }, []);

  const handleModeChange = (mode: MapMode) => {
    setMapMode(mode);
    setPopup(null);
    setOpenDropdown(null);
    const next = new URLSearchParams(searchParams);
    if (mode === 'heatmap') next.delete('mode');
    else next.set('mode', mode);
    setSearchParams(next, { replace: true });
  };

  const toggleDropdown = (id: string) => {
    setOpenDropdown((prev) => (prev === id ? null : id));
  };

  const handlePinClick = (key: string) => {
    const pins = filteredPins.filter((p) => jibunKeyOf(p) === key);
    if (pins.length > 0) setPopup({ type: 'deal', key, pins });
  };

  const toggleFacility = (key: FacilityKey) => {
    setFacilityKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleDashboardOpen = () => {
    setRouteTransition(true);
    window.setTimeout(() => navigate('/dashboard'), 360);
  };

  return (
    <main className="map-redesign relative h-screen w-screen overflow-hidden bg-bg text-text">
      <h1 className="sr-only">서울 주거 지도</h1>

      <HeatMap
        adongs={scoresData}
        activeLayer={heatmapActiveLayer}
        heatmapVisible={heatmapVisible}
        mode={heatmapMode}
        matchCounts={matchCounts}
        onAdongClick={mapMode === 'heatmap' ? (adong) => setPopup({ type: 'adong', adong }) : undefined}
      >
        <CurrentLocationLayer
          requestId={locateRequest}
          onError={(message) => flash(message)}
        />
        <SearchFlyTo item={selectedSearchItem} />
        {showRealEstatePins ? (
          <TransactionPinLayer
            pins={filteredPins}
            selectedJibun={selectedJibun}
            onPinClick={handlePinClick}
            onMapStateChange={setMapState}
            suppressTooltips={popup != null}
          />
        ) : (
          <MapStateProbe onMapStateChange={setMapState} />
        )}
      </HeatMap>

      <section className="absolute left-5 top-5 z-[500] grid justify-items-start gap-2" aria-label="지도 검색과 필터">
        <div className="relative">
          <label className="flex h-11 w-[430px] items-center gap-3 rounded-card border border-border bg-white/95 px-3 shadow-lg backdrop-blur">
            <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center text-[18px] font-semibold text-text-muted" aria-hidden="true">⌕</span>
            <input
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && searchResults[0]) {
                  if (hasValidCoordinate(searchResults[0])) {
                    setSelectedSearchItem(searchResults[0]);
                    setPopup({ type: 'search', item: searchResults[0] });
                  } else {
                    flash('좌표가 없는 검색 결과입니다.');
                  }
                }
              }}
              placeholder="지역, 지하철역, 학교 등 검색"
              className="min-w-0 flex-1 border-0 bg-transparent text-[14px] outline-none placeholder:text-text-subtle"
            />
          </label>
          {(searchLoading || searchResults.length > 0) ? (
            <div className="absolute left-0 top-[calc(100%+6px)] z-[650] w-[430px] overflow-hidden rounded-card border border-border bg-white/95 shadow-xl backdrop-blur">
              {searchLoading ? <div className="px-3 py-2 text-[13px] font-semibold text-text-muted">검색 중...</div> : null}
              {searchResults.map((item) => (
                <button key={item.id} type="button" onClick={() => { if (!hasValidCoordinate(item)) { flash('좌표가 없는 검색 결과입니다.'); return; } setSelectedSearchItem(item); setPopup({ type: 'search', item }); setSearchText(item.name); setSearchResults([]); }} className="block w-full border-t border-border/70 px-3 py-2 text-left transition first:border-t-0 hover:bg-[var(--color-heatmap-1)]">
                  <span className="block text-[13px] font-semibold text-text">{item.name}</span>
                  <span className="mt-0.5 block truncate text-[12px] text-text-muted">{item.label}{item.address ? ' · ' + item.address : ''}</span>
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="grid w-[var(--map-control-width)] grid-cols-4 rounded-card border border-border bg-white/95 p-1 shadow-lg backdrop-blur" role="group" aria-label="지도 모드">
          <SegmentButton active={mapMode === 'plain'} onClick={() => handleModeChange('plain')}>지도</SegmentButton>
          <SegmentButton active={mapMode === 'heatmap'} onClick={() => handleModeChange('heatmap')}>히트맵</SegmentButton>
          <SegmentButton active={mapMode === 'realestate'} onClick={() => handleModeChange('realestate')}>부동산</SegmentButton>
          <SegmentButton active={mapMode === 'facility'} onClick={() => handleModeChange('facility')}>시설</SegmentButton>
        </div>

        {mapMode === 'plain' ? (
          <ModeGuide title="지도">
            기본 지도를 표시합니다. 검색한 지역이나 지점을 중심으로 지도를 탐색할 수 있습니다.
          </ModeGuide>
        ) : null}

        {mapMode === 'heatmap' ? (
          <div className="w-[152px] rounded-card border border-border bg-white/95 p-2 shadow-lg backdrop-blur">
            <div className="mb-2 grid w-full grid-cols-2 rounded-[12px] border border-[var(--color-heatmap-2)] bg-white/80 p-1" role="group" aria-label="지역 단위">
              <button type="button" onClick={() => setRegionLevel('adong')} className={`h-8 rounded-[9px] px-3 text-[13px] font-semibold transition ${regionLevel === 'adong' ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm' : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}>행정동</button>
              <button type="button" onClick={() => { setRegionLevel('ldong'); flash('법정동 보기는 백엔드/GeoJSON 연결 후 활성화됩니다.'); }} className={`h-8 rounded-[9px] px-3 text-[13px] font-semibold transition ${regionLevel === 'ldong' ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm' : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}>법정동</button>
            </div>
            <div className="grid w-full gap-1.5">
              {HEAT_LAYERS.map((layer) => (
                <div key={layer.key} className="group relative">
                  <button
                    type="button"
                    onClick={() => {
                      setHeatLayer(layer.key);
                      if (layer.key === 'safety') flash('안전 지수는 현재 구 기반 API 연결 전이라 종합 색상을 임시 사용합니다.');
                    }}
                    className={`relative flex h-9 w-full items-center rounded-[var(--map-control-radius)] border px-3 pr-7 text-left text-[13px] font-semibold shadow-sm transition ${
                      heatLayer === layer.key
                        ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]'
                        : 'border-border bg-white/95 text-text hover:bg-[var(--color-heatmap-1)]'
                    }`}
                  >
                    <span>{layer.label}</span>
                    <span
                      aria-label={`${layer.label} 계산 방식`}
                      className="absolute right-1.5 top-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full border border-border/80 bg-white/70 text-[9px] font-bold leading-none text-text-subtle"
                    >
                      i
                    </span>
                  </button>
                  <div className="pointer-events-none absolute left-[calc(100%+8px)] top-0 z-[700] hidden w-[280px] rounded-card border border-[var(--color-heatmap-2)] bg-white p-3 text-[12px] leading-5 text-text shadow-xl group-hover:block">
                    <strong className="mb-1 block text-[13px] text-[var(--color-heatmap-5)]">{layer.label}</strong>
                    {HEAT_LAYER_DESCRIPTIONS[layer.key]}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {mapMode === 'heatmap' ? (
          <ModeGuide title="히트맵">
            선택한 점수를 기준으로 {regionLevel === 'adong' ? '행정동별' : '법정동별'} 분포를 색으로 보여줍니다. 동을 클릭하면 주요 점수와 순위를 확인할 수 있습니다.
          </ModeGuide>
        ) : null}

        {mapMode === 'realestate' ? (
          <div className="flex items-start gap-2">
            <div className="grid w-[152px] gap-2 rounded-card border border-border bg-white/95 p-2 shadow-lg backdrop-blur">
            <DropdownButton id="period" label={PERIOD_LABELS[filters.period]} active width="w-full" open={openDropdown === 'period'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <ChoiceList
                selected={filters.period}
                onSelect={(value) => { patch({ period: value as ExplorePeriod }); setOpenDropdown(null); }}
                items={Object.entries(PERIOD_LABELS).map(([value, label]) => ({ value, label }))}
              />
            </DropdownButton>
            <DropdownButton id="deal-type" label={formatDealTypes(filters.deal_types)} active width="w-full" open={openDropdown === 'deal-type'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <div className="flex flex-wrap gap-1.5">
                {(Object.keys(DEAL_TYPE_LABELS) as ExploreDealType[]).map((type) => {
                  const active = filters.deal_types.includes(type);
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => {
                        const next = active
                          ? filters.deal_types.filter((t) => t !== type)
                          : [...filters.deal_types, type];
                        patch({ deal_types: next.length > 0 ? next : [type] });
                      }}
                      className={`h-8 rounded-[6px] px-2 text-[12px] font-semibold transition ${active ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'bg-surface-alt text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}
                    >
                      {DEAL_TYPE_LABELS[type]}
                    </button>
                  );
                })}
              </div>
            </DropdownButton>
            <DropdownButton id="deposit" label={formatRangeLabel('보증금', filters.deposit_min, filters.deposit_max, RANGE_ALL.deposit.max)} width="w-full" open={openDropdown === 'deposit'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <RangePanel
                title="보증금 범위"
                unit="만원"
                min={filters.deposit_min}
                max={filters.deposit_max}
                onChange={(deposit_min, deposit_max) => patch({ deposit_min, deposit_max })}
                presets={[{ label: '전체', min: RANGE_ALL.deposit.min, max: RANGE_ALL.deposit.max }, { label: '3천 이하', min: 0, max: 3000 }, { label: '5천 이하', min: 0, max: 5000 }, { label: '1억 이하', min: 0, max: 10000 }]}
              />
            </DropdownButton>
            <DropdownButton id="monthly" label={formatRangeLabel('월세', filters.monthly_min, filters.monthly_max, RANGE_ALL.monthly.max)} width="w-full" open={openDropdown === 'monthly'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <RangePanel
                title="월세 범위"
                unit="만원"
                min={filters.monthly_min}
                max={filters.monthly_max}
                onChange={(monthly_min, monthly_max) => patch({ monthly_min, monthly_max })}
                presets={[{ label: '전체', min: RANGE_ALL.monthly.min, max: RANGE_ALL.monthly.max }, { label: '50 이하', min: 0, max: 50 }, { label: '80 이하', min: 0, max: 80 }, { label: '120 이하', min: 0, max: 120 }]}
              />
            </DropdownButton>
            <DropdownButton id="converted" label={formatRangeLabel('환산월세', filters.converted_min, filters.converted_max, RANGE_ALL.converted.max)} width="w-full" open={openDropdown === 'converted'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <RangePanel
                title="환산월세 범위"
                unit="만원"
                min={filters.converted_min}
                max={filters.converted_max}
                onChange={(converted_min, converted_max) => patch({ converted_min, converted_max })}
                presets={[{ label: '전체', min: RANGE_ALL.converted.min, max: RANGE_ALL.converted.max }, { label: '60 이하', min: 0, max: 60 }, { label: '100 이하', min: 0, max: 100 }, { label: '150 이하', min: 0, max: 150 }]}
              />
            </DropdownButton>
            <DropdownButton id="area" label={formatRangeLabel('면적', filters.area_min, filters.area_max, RANGE_ALL.area.max, 'm²')} width="w-full" open={openDropdown === 'area'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <RangePanel
                title="면적 범위"
                unit="m²"
                min={filters.area_min}
                max={filters.area_max}
                onChange={(area_min, area_max) => patch({ area_min, area_max })}
                presets={[{ label: '전체', min: RANGE_ALL.area.min, max: RANGE_ALL.area.max }, { label: '10-20m²', min: 10, max: 20 }, { label: '20-40m²', min: 20, max: 40 }, { label: '40-60m²', min: 40, max: 60 }]}
              />
            </DropdownButton>
            <ResetButton onClick={reset}>초기화</ResetButton>
            </div>
            <div className="group relative mt-2">
              <button type="button" aria-label="부동산 지도 안내" className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-border/80 bg-white/70 text-[11px] font-bold text-text-subtle shadow-sm backdrop-blur focus:outline-none">i</button>
              <div className="pointer-events-none absolute left-[calc(100%+8px)] top-0 z-[700] hidden w-[300px] rounded-card border border-[var(--color-heatmap-2)] bg-white p-3 text-[12px] leading-5 text-text shadow-xl group-hover:block">
                지도에 표시되는 포인터는 환산월세 기준으로 보조 안내됩니다. 단독/다가구는 원천 데이터 특성상 주소와 좌표를 알기 어려워 표시되지 않습니다.
              </div>
            </div>
          </div>
        ) : null}

        {mapMode === 'realestate' ? (
          <ModeGuide title="부동산">
            선택한 조건에 맞는 거래 내역을 지도에 표시합니다. 지도를 확대하면 개별 거래 위치를 확인할 수 있습니다.
          </ModeGuide>
        ) : null}

        {mapMode === 'facility' ? (
          <div className="grid w-[152px] justify-items-start gap-1.5 rounded-card border border-border bg-white/95 p-2 shadow-lg backdrop-blur">
            {(['university', 'park', 'subway', 'bus', 'hospital', 'pharmacy', 'restaurant', 'cafe', 'mart', 'library'] as FacilityKey[]).map((key) => (
              <FilterButton key={key} active={facilityKeys.has(key)} onClick={() => toggleFacility(key)} className="w-full">
                {FACILITY_LABELS[key]}
              </FilterButton>
            ))}
            <ResetButton onClick={() => setFacilityKeys(new Set(['university', 'park', 'subway', 'bus']))}>초기화</ResetButton>
          </div>
        ) : null}

        {mapMode === 'facility' ? (
          <ModeGuide title="시설">
            선택한 시설을 지도 위에 표시합니다. 지도를 확대하면 주변 시설 위치를 더 자세히 확인할 수 있습니다.
          </ModeGuide>
        ) : null}
      </section>

      <Link
        to={user ? '/mypage' : '/login'}
        className="app-floating-button fixed right-6 top-6 z-[1200] h-10 min-h-10"
      >
        {user ? '마이페이지' : '로그인'}
      </Link>

      <div className="absolute bottom-6 left-6 z-[500] flex items-center gap-2">
        <button
          type="button"
          onClick={handleDashboardOpen}
          className="app-floating-button"
        >
          대시보드 보기
        </button>
        <button
          type="button"
          onClick={() => setLocateRequest((v) => v + 1)}
          aria-label="현재 위치로 이동"
          title="현재 위치로 이동"
          className="map-icon-button"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="6.5" />
            <circle cx="12" cy="12" r="1.8" fill="currentColor" stroke="none" />
            <path d="M12 2.75v3M12 18.25v3M2.75 12h3M18.25 12h3" />
          </svg>
        </button>
        <button
          type="button"
          aria-label="집 기준 설정"
          title="집 기준 설정"
          onClick={() => flash('집 기준 설정은 추후 연결할 예정입니다.')}
          className="map-icon-button"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 10.75 12 4l8 6.75" />
            <path d="M6.5 9.75V20h11V9.75" />
            <path d="M10 20v-5.5h4V20" />
          </svg>
        </button>
      </div>

      <button
        type="button"
        onClick={openAiPanel}
        className="app-floating-button fixed bottom-6 right-6 z-[1200]"
      >
        AI에게 물어보기
      </button>
      {mapMode === 'heatmap' ? (
        <div className="absolute bottom-6 left-1/2 z-[500] flex -translate-x-1/2 items-center gap-3 rounded-card border border-border bg-white/95 px-4 py-2 text-[13px] font-semibold text-text shadow-lg backdrop-blur">
          <span>낮음</span>
          <span className="h-3 w-[180px] rounded-full bg-gradient-to-r from-[var(--color-heatmap-1)] via-[var(--color-heatmap-3)] to-[var(--color-heatmap-5)]" />
          <span>높음</span>
          <strong className="text-[var(--color-heatmap-5)]">{HEAT_LAYERS.find((l) => l.key === heatLayer)?.label}</strong>
        </div>
      ) : null}

      {scoresLoading ? <StatusPill>지도 데이터를 불러오는 중입니다.</StatusPill> : null}
      {scoresError ? <StatusPill tone="danger">지도 데이터를 불러오지 못했습니다.</StatusPill> : null}
      {mapMode === 'realestate' && matchQuery.isFetching ? <StatusPill>부동산 데이터를 불러오는 중입니다.</StatusPill> : null}
      {toast ? <StatusPill position="top-[88px]" tone="dark">{toast}</StatusPill> : null}

      <MapPopup popup={popup} onClose={() => setPopup(null)} heatLayer={heatLayer} ranks={ranks} rankTotal={scoresData.length} />

      {routeTransition ? (
        <div className="map-route-transition map-route-transition--out" aria-hidden="true">
          <div className="map-route-transition__frame" />
        </div>
      ) : null}
    </main>
  );
}

function StatusPill({ children, tone = 'dark', position = 'top-5' }: { children: React.ReactNode; tone?: 'dark' | 'danger'; position?: string }) {
  return (
    <div className={`absolute left-1/2 z-[560] -translate-x-1/2 rounded-[8px] px-4 py-2 text-[13px] font-semibold shadow-lg ${position} ${tone === 'danger' ? 'bg-danger text-white' : 'bg-[var(--map-status-bg)] text-white'}`}>
      {children}
    </div>
  );
}



function hasValidCoordinate(item: MapSearchItem | null): item is MapSearchItem {
  return !!item && Number.isFinite(item.lat) && Number.isFinite(item.lng);
}

function SearchFlyTo({ item }: { item: MapSearchItem | null }) {
  const map = useMap();
  useEffect(() => {
    if (!hasValidCoordinate(item)) return;
    map.flyTo([item.lat, item.lng], Math.max(map.getZoom(), 15), { duration: 0.6 });
  }, [item, map]);
  return null;
}

function CurrentLocationLayer({
  requestId,
  onError,
}: {
  requestId: number;
  onError: (message: string) => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (requestId === 0) return;
    if (!navigator.geolocation) {
      onError('현재 위치를 지원하지 않는 브라우저입니다.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        map.flyTo(
          [position.coords.latitude, position.coords.longitude],
          Math.max(map.getZoom(), 15),
          { duration: 0.6 },
        );
      },
      () => onError('현재 위치 권한을 확인해주세요.'),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60_000 },
    );
  // Intentionally depend only on requestId: parent passes an inline onError callback.
  // Including it here retriggers flyTo on unrelated renders, making the map feel locked.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, requestId]);

  return null;
}

function MapStateProbe({ onMapStateChange }: { onMapStateChange: (state: MapState) => void }) {
  const map = useMap();
  useEffect(() => {
    const b = map.getBounds();
    onMapStateChange({
      bbox: { lng1: b.getWest(), lat1: b.getSouth(), lng2: b.getEast(), lat2: b.getNorth() },
      zoom: map.getZoom(),
    });
  }, [map, onMapStateChange]);
  useMapEvents({
    moveend: () => {
      const b = map.getBounds();
      onMapStateChange({ bbox: { lng1: b.getWest(), lat1: b.getSouth(), lng2: b.getEast(), lat2: b.getNorth() }, zoom: map.getZoom() });
    },
    zoomend: () => {
      const b = map.getBounds();
      onMapStateChange({ bbox: { lng1: b.getWest(), lat1: b.getSouth(), lng2: b.getEast(), lat2: b.getNorth() }, zoom: map.getZoom() });
    },
  });
  return null;
}
