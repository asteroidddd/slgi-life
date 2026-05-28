import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import L from 'leaflet';
import { CircleMarker, Marker, useMap, useMapEvents } from 'react-leaflet';
import { useQuery } from '@tanstack/react-query';

import HeatMap from '@/components/Map/HeatMap';
import type { ScoreLayerKey } from '@/components/Map/HeatMap';
import TransactionPinLayer from '@/components/Map/TransactionPinLayer';
import type { MapState } from '@/components/Map/TransactionPinLayer';
import { useAuth } from '@/contexts/AuthContext';
import { useAdongMatchCounts } from '@/hooks/useAdongMatchCounts';
import { useAdongScores, useLdongScores } from '@/hooks/useAdongs';
import { useRentDealCache } from '@/hooks/useRentDealCache';
import { useStudioMatchFilters } from '@/hooks/useStudioMatchFilters';
import { getAmenitiesBbox, getMapSearch, getRentConversionRate, getRentDealDetail } from '@/lib/api';
import { setDashboardMiniMapTransitionTarget } from '@/lib/dashboardTransition';
import { HEATMAP_COLORS_ORDERED } from '@/lib/colors';
import { MONTHLY_CONVERSION_RATE } from '@/lib/rent';
import { DEFAULT_WEIGHTS } from '@/types/api';
import type {
  AdongScore,
  AmenityBboxItem,
  ExploreDealType,
  ExplorePeriod,
  MapSearchItem,
  MatchFilters,
  RentDealCachePin,
  RentDealCacheResponse,
  RentDealPin,
} from '@/types/api';

import 'leaflet/dist/leaflet.css';

type MapMode = 'plain' | 'heatmap' | 'realestate' | 'facility';
type RegionLevel = 'adong' | 'ldong';
type FacilityKey =
  | 'subway_station'
  | 'bus_stop'
  | 'university'
  | 'park'
  | 'library'
  | 'convenience'
  | 'mart'
  | 'restaurant'
  | 'cafe'
  | 'nightlife'
  | 'hospital'
  | 'dental'
  | 'pharmacy'
  | 'pet'
  | 'laundry'
  | 'beauty'
  | 'oliveyoung'
  | 'gym'
  | 'book_stationery'
  | 'pc_room';

type SelectedPopup =
  | { type: 'adong'; adong: AdongScore }
  | { type: 'deal'; key: string; pins: RentDealPin[] }
  | { type: 'deal_loading'; key: string }
  | { type: 'facility'; title: string; description: string }
  | { type: 'search'; item: MapSearchItem }
  | null;

type DataSourcePanel = 'terms' | 'privacy' | 'data' | null;
type RealEstateHelperTab = 'checklist' | 'calculator' | 'analysis' | 'links';

const HEAT_LAYERS: Array<{ key: ScoreLayerKey; label: string }> = [
  { key: 'composite', label: '종합 점수' },
  { key: 'rent', label: '부동산 점수' },
  { key: 'transit', label: '교통 점수' },
  { key: 'amenity', label: '편의시설 점수' },
  { key: 'safety', label: '안전 지수' },
];

const HEAT_LAYER_DESCRIPTIONS: Record<ScoreLayerKey, string> = {
  composite: '기본 가중치 33/33/34로 부동산·편의시설·교통 점수를 합산한 값입니다.',
  rent: '최근 365일 실거래의 (월세 + 보증금×0.005) / 면적(m²)을 계산하고, 상하위 5%를 줄인 평균을 사용합니다. 값이 낮을수록 높은 점수입니다.',
  transit: '가장 가까운 지하철역 거리 점수 60%와 면적당 버스정류장 밀도 점수 40%를 합산합니다. 지하철 거리는 1km를 기준으로 멀수록 낮아집니다.',
  amenity: '면적당 생활시설 밀도 60.9%, 의료시설 밀도 10.8%, 공원 면적 비율 28.3%를 합산합니다. 생활/의료 밀도는 로그 정규화합니다.',
  safety: '교통사고, 화재, 범죄, 생활안전, 자살, 감염병 6개 지역안전등급을 평균한 구 단위 지표입니다. 등급이 낮을수록 안전한 원자료를 0~100 점수로 변환해 표시합니다.',
};

const DEAL_TYPE_LABELS: Record<ExploreDealType, string> = {
  yeonlip: '연립',
  dasedae: '다세대',
  yeonlip_dasedae: '연립다세대',
  dagagu: '다가구',
  danok: '단독',
  officetel: '오피스텔',
  apt: '아파트',
};

const DEAL_TYPE_FILTER_OPTIONS: ExploreDealType[] = ['yeonlip', 'dasedae', 'dagagu', 'danok', 'officetel', 'apt'];

const PERIOD_LABELS: Record<ExplorePeriod, string> = {
  '3m': '최근 3개월',
  '6m': '최근 6개월',
  '12m': '최근 1년',
  '24m': '최근 2년',
  all: '전체 기간',
};

const FACILITY_LABELS: Record<FacilityKey, string> = {
  subway_station: '지하철역',
  bus_stop: '버스정류장',
  university: '대학',
  park: '공원',
  library: '도서관',
  convenience: '편의점',
  mart: '마트',
  restaurant: '음식점',
  cafe: '카페',
  nightlife: '주점',
  hospital: '병원',
  dental: '치과',
  pharmacy: '약국',
  pet: '반려동물',
  laundry: '세탁',
  beauty: '미용',
  oliveyoung: '올리브영',
  gym: '체육시설',
  book_stationery: '서점/문구',
  pc_room: 'PC방',
};

const FACILITY_ORDER: FacilityKey[] = [
  'subway_station',
  'bus_stop',
  'university',
  'park',
  'library',
  'convenience',
  'mart',
  'restaurant',
  'cafe',
  'nightlife',
  'hospital',
  'dental',
  'pharmacy',
  'pet',
  'laundry',
  'beauty',
  'oliveyoung',
  'gym',
  'book_stationery',
  'pc_room',
];

const FACILITY_ICONS: Record<FacilityKey, string> = {
  subway_station: '🚇',
  bus_stop: '🚌',
  university: '🎓',
  park: '🌳',
  library: '📚',
  convenience: '🏪',
  mart: '🛒',
  restaurant: '🍜',
  cafe: '☕',
  nightlife: '🍺',
  hospital: '🏥',
  dental: '🦷',
  pharmacy: '💊',
  pet: '🐾',
  laundry: '🧺',
  beauty: '✂',
  oliveyoung: '🫒',
  gym: '🏋',
  book_stationery: '✏',
  pc_room: `<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="4" width="16" height="11" rx="1.5"/><path d="M10 19h4"/><path d="M12 15v4"/><path d="M7 21h10"/></svg>`,
};

const RANGE_ALL = {
  deposit: { min: 0, max: 999_999 },
  monthly: { min: 0, max: 9_999 },
  converted: { min: 0, max: 9_999 },
  area: { min: 0, max: 10_000 },
};

const MAX_VISIBLE_RENT_PINS = 2500;

const DEFAULT_ANNUAL_CONVERSION_RATE = Number((MONTHLY_CONVERSION_RATE * 12 * 100).toFixed(3));

function formatRangeLabel(label: string, min: number, max: number, allMax: number, unit = '') {
  if (min <= 0 && max >= allMax) return `${label} 전체`;
  return `${label} ${min.toLocaleString()}-${max.toLocaleString()}${unit}`;
}

function periodToMinYmd(period: ExplorePeriod, today: Date = new Date()): number | null {
  if (period === 'all') return null;
  const days = period === '3m' ? 90 : period === '6m' ? 180 : period === '12m' ? 365 : 730;
  const t = new Date(today);
  t.setDate(t.getDate() - days);
  return t.getFullYear() * 10000 + (t.getMonth() + 1) * 100 + t.getDate();
}

function expandDealTypesForFiltering(types: ExploreDealType[]): ExploreDealType[] {
  const expanded = [...types];
  if (types.includes('yeonlip') && types.includes('dasedae') && !expanded.includes('yeonlip_dasedae')) {
    expanded.push('yeonlip_dasedae');
  }
  return expanded;
}

function applyClientCacheFilter(
  data: RentDealCacheResponse | undefined,
  f: MatchFilters,
  bbox: MapState['bbox'] | null,
): RentDealCachePin[] {
  if (!data) return [];
  const expandedDealTypes = expandDealTypesForFiltering(f.deal_types);
  const minYmd = periodToMinYmd(f.period);
  const pins: RentDealCachePin[] = [];

  for (const row of data.rows) {
    const [id, typeCode, deposit, monthlyRent, convertedRent, areaM2, lng, lat, contractYmd] = row;
    if (lng == null || lat == null) continue;
    if (bbox && (lng < bbox.lng1 || lng > bbox.lng2 || lat < bbox.lat1 || lat > bbox.lat2)) continue;
    if (minYmd != null && contractYmd < minYmd) continue;

    const dealType = data.type_map[typeCode];
    if (!expandedDealTypes.includes(dealType)) continue;
    if (f.filter_mode === 'raw') {
      if (deposit < f.deposit_min || deposit > f.deposit_max) continue;
      if (monthlyRent < f.monthly_min || monthlyRent > f.monthly_max) continue;
    } else {
      if (convertedRent < f.converted_min || convertedRent > f.converted_max) continue;
    }
    if (areaM2 == null || areaM2 < f.area_min || areaM2 > f.area_max) continue;

    pins.push({
      id,
      deal_type: dealType,
      area_m2: areaM2,
      deposit,
      monthly_rent: monthlyRent,
      converted_rent: convertedRent,
      lng,
      lat,
      contract_ymd: contractYmd,
    });
    if (pins.length >= MAX_VISIBLE_RENT_PINS) break;
  }
  return pins;
}

function formatDealTypes(types: ExploreDealType[]) {
  if (types.length >= 5) return '전체 유형';
  return types.map((t) => DEAL_TYPE_LABELS[t]).join(', ');
}

function convertByAnnualRate(deposit: number, monthlyRent: number, annualRate: number) {
  const safeDeposit = Math.max(0, Number.isFinite(deposit) ? deposit : 0);
  const safeMonthly = Math.max(0, Number.isFinite(monthlyRent) ? monthlyRent : 0);
  const safeRate = Math.max(0, Number.isFinite(annualRate) ? annualRate : DEFAULT_ANNUAL_CONVERSION_RATE);
  return Math.floor(safeMonthly + (safeDeposit * (safeRate / 100)) / 12);
}

function RealEstateHelperPanel({
  open,
  onToggle,
}: {
  open: boolean;
  onToggle: () => void;
}) {
  const [activeTab, setActiveTab] = useState<RealEstateHelperTab>('checklist');
  const [deposit, setDeposit] = useState(5000);
  const [monthlyRent, setMonthlyRent] = useState(60);
  const [annualRate, setAnnualRate] = useState(DEFAULT_ANNUAL_CONVERSION_RATE);
  const [listingAddress, setListingAddress] = useState('서울특별시 관악구 신림동');
  const [listingDeposit, setListingDeposit] = useState(1000);
  const [listingMonthly, setListingMonthly] = useState(65);
  const convertedRent = convertByAnnualRate(deposit, monthlyRent, annualRate);
  const listingConvertedRent = convertByAnnualRate(listingDeposit, listingMonthly, annualRate);
  const conversionRateQuery = useQuery({
    queryKey: ['rent-deals', 'conversion-rate'],
    queryFn: getRentConversionRate,
    staleTime: 60 * 60 * 1000,
    enabled: open,
  });

  useEffect(() => {
    if (typeof conversionRateQuery.data?.annual_rate !== 'number') return;
    setAnnualRate(Number(conversionRateQuery.data.annual_rate.toFixed(3)));
  }, [conversionRateQuery.data?.annual_rate]);

  return (
    <div className="pointer-events-none relative w-[132px]">
      <div className="pointer-events-auto grid w-full gap-2">
        <button
          type="button"
          onClick={onToggle}
          className={`flex h-10 w-full items-center justify-center gap-1.5 rounded-[var(--map-control-radius)] border px-2 text-[12px] font-semibold tracking-normal shadow-lg backdrop-blur transition ${
            open
              ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]'
              : 'border-[var(--color-heatmap-2)]/50 bg-white/95 text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
          }`}
          aria-expanded={open}
        >
          <span className="text-[12px] leading-none" aria-hidden="true">✓</span>
          <span className="truncate">부동산 도우미</span>
        </button>

        <div className="group relative z-[300] w-max">
          <button type="button" aria-label="부동산 지도 안내" className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-border/80 bg-white/70 text-[11px] font-bold text-text-subtle shadow-sm backdrop-blur focus:outline-none">i</button>
          <div className="pointer-events-none absolute left-[calc(100%+8px)] top-0 z-[1000] hidden w-[340px] rounded-card border border-[var(--color-heatmap-2)] bg-white p-3 text-[12px] leading-5 text-text shadow-xl group-hover:block">
            <p className="m-0">환산월세는 한국부동산원 전월세전환율을 KOSIS에서 받아 보증금을 월세로 환산해 계산합니다.<br />환산월세 기준을 쓰면 보증금/월세 필터는 잠기고, 보증금/월세 기준을 쓰면 환산월세 필터가 잠깁니다.</p>
            <p className="m-0 mt-1">과거 실거래 원천 데이터 일부는 연립과 다세대가 연립다세대로 통합되어 있어 두 유형을 함께 볼 때 통합 데이터도 같이 반영됩니다.<br />단독/다가구는 원천 데이터 특성상 주소와 좌표를 알기 어려워 표시되지 않습니다.</p>
          </div>
        </div>
      </div>

      {open ? (
        <aside className="pointer-events-auto absolute left-[calc(100%+8px)] top-[-104px] z-[1200] grid max-h-[min(820px,calc(100vh-24px))] w-[500px] grid-rows-[auto_auto_1fr] overflow-hidden rounded-card border border-[var(--color-heatmap-2)]/50 bg-white/95 text-text shadow-2xl backdrop-blur" aria-label="부동산 도우미">
          <header className="border-b border-border/70 px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="m-0 text-[15px] font-bold text-text">부동산 도우미</h2>
                <p className="m-0 mt-1 text-[12px] leading-5 text-text-muted">계약 전 확인, 환산월세 계산, 실거래 기반 가격 분석, 외부 링크를 한 곳에서 봅니다.</p>
              </div>
              <button type="button" onClick={onToggle} className="h-7 w-7 rounded-[6px] bg-surface-alt text-[16px] text-text-muted hover:bg-border/60" aria-label="부동산 도우미 닫기">×</button>
            </div>
          </header>

          <div className="grid grid-cols-4 gap-1 border-b border-border/70 bg-surface-alt/80 p-2">
            {([
              ['checklist', '체크리스트'],
              ['calculator', '환산월세'],
              ['analysis', '매물 분석'],
              ['links', '외부 링크'],
            ] as Array<[RealEstateHelperTab, string]>).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`h-8 rounded-[9px] text-[12px] font-bold transition ${
                  activeTab === tab
                    ? 'bg-white text-[var(--color-heatmap-5)] shadow-sm'
                    : 'text-text-muted hover:bg-white/70 hover:text-text'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="overflow-y-auto p-3">
            {activeTab === 'checklist' ? <RealEstateChecklist /> : null}
            {activeTab === 'calculator' ? (
              <RealEstateCalculator
                deposit={deposit}
                monthlyRent={monthlyRent}
                annualRate={annualRate}
                convertedRent={convertedRent}
                onDepositChange={setDeposit}
                onMonthlyRentChange={setMonthlyRent}
                onAnnualRateChange={setAnnualRate}
                rateSource={conversionRateQuery.data?.source ?? 'KOSIS 한국부동산원 전월세전환율'}
                rateLoading={conversionRateQuery.isLoading}
              />
            ) : null}
            {activeTab === 'analysis' ? (
              <RealEstateListingAnalysis
                address={listingAddress}
                deposit={listingDeposit}
                monthlyRent={listingMonthly}
                convertedRent={listingConvertedRent}
                onAddressChange={setListingAddress}
                onDepositChange={setListingDeposit}
                onMonthlyRentChange={setListingMonthly}
              />
            ) : null}
            {activeTab === 'links' ? <RealEstateLinks /> : null}
          </div>
        </aside>
      ) : null}
    </div>
  );
}

function RealEstateChecklist() {
  return (
    <div className="grid gap-2">
      <ChecklistCard title="계약 전" hint="가격과 권리관계가 안전한지 먼저 거릅니다." items={[
        '실거래가, 주변 매물, KB/부동산원 시세를 비교해 가격이 과도하지 않은지 확인',
        '전세가율 확인. 전세가가 매매가의 80%를 넘으면 위험 신호로 보기',
        '등기부등본으로 소유자, 근저당, 가압류, 압류, 가처분 확인',
        '신탁등기가 있으면 신탁원부와 신탁회사 임대 동의 여부 확인',
        '건축물대장으로 위반건축물, 무허가, 근린생활시설 여부 확인',
        '임대인 국세·지방세 체납 열람 가능 여부 확인',
        'HUG 등 전세보증금 반환보증 가입 가능 여부 확인',
        '다가구/단독이면 선순위 임차인과 선순위 보증금 규모 확인',
      ]} />
      <ChecklistCard title="계약 시" hint="계약 당사자와 계약서 문구를 확인합니다." items={[
        '임대인 신분증과 등기부 소유자 일치 확인',
        '공동소유면 소유자 전원 동의 또는 계약 참여 여부 확인',
        '법인 임대인이면 법인등기, 대표자 신분, 법인 인감 확인',
        '대리인 계약이면 위임장, 인감증명서, 임대인 직접 연락 확인',
        '공인중개사 등록 상태, 정상 영업 여부, 공제증서 확인',
        '계약금·잔금 입금 계좌가 임대인 명의인지 확인',
        '잔금 다음날까지 근저당 등 권리변동 금지 특약 검토',
        '보증보험 가입 협조, 권리하자·체납 발견 시 계약 해제 특약 검토',
      ]} />
      <ChecklistCard title="잔금/입주 후" hint="잔금 전후 권리 변동과 보증 절차를 마무리합니다." items={[
        '잔금 직전 등기부등본을 다시 발급해 권리 변동 확인',
        '입주 즉시 전입신고와 확정일자 처리',
        '주택 임대차 계약 신고 대상이면 신고 여부 확인',
        '전세보증금 반환보증 가입 완료',
        '입주 후 일정 기간 뒤 등기부를 다시 확인해 추가 권리 설정 여부 확인',
      ]} />
      <p className="m-0 text-[11px] leading-5 text-text-subtle">체크 상태는 저장하지 않고 현재 화면에서만 유지됩니다.</p>
    </div>
  );
}

function ChecklistCard({ title, hint, items }: { title: string; hint: string; items: string[] }) {
  return (
    <section className="rounded-card border border-border bg-white p-3">
      <strong className="block text-[13px] text-[var(--color-heatmap-5)]">{title}</strong>
      <span className="mt-1 block text-[11px] leading-4 text-text-muted">{hint}</span>
      <ul className="m-0 mt-2 grid gap-1.5 p-0">
        {items.map((item, index) => {
          const id = `realestate-check-${title}-${index}`;
          return (
            <li key={item} className="grid grid-cols-[18px_1fr] items-start gap-2 text-[12px] leading-5 text-text-muted">
              <input id={id} type="checkbox" className="peer mt-1 h-[15px] w-[15px] accent-[var(--color-heatmap-5)]" />
              <label htmlFor={id} className="cursor-pointer peer-checked:text-text-subtle">{item}</label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function RealEstateCalculator({
  deposit,
  monthlyRent,
  annualRate,
  convertedRent,
  rateSource,
  rateLoading,
  onDepositChange,
  onMonthlyRentChange,
  onAnnualRateChange,
}: {
  deposit: number;
  monthlyRent: number;
  annualRate: number;
  convertedRent: number;
  rateSource: string;
  rateLoading: boolean;
  onDepositChange: (value: number) => void;
  onMonthlyRentChange: (value: number) => void;
  onAnnualRateChange: (value: number) => void;
}) {
  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 gap-2">
        <NumberField label="보증금" value={deposit} onChange={onDepositChange} step={100} />
        <NumberField label="월세" value={monthlyRent} onChange={onMonthlyRentChange} step={5} />
      </div>
      <div className="grid grid-cols-[1fr_auto] items-end gap-2">
        <NumberField label="전환율" value={annualRate} onChange={onAnnualRateChange} step={0.05} />
        <span className="pb-2 text-[11px] font-semibold text-text-muted">연 %</span>
      </div>
      <div className="rounded-card border border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] p-3">
        <span className="block text-[11px] font-bold text-text-muted">계산된 환산월세</span>
        <div className="mt-1 flex items-baseline gap-2 text-[var(--color-heatmap-5)]">
          <strong className="text-[34px] leading-none">{convertedRent}</strong>
          <span className="text-[12px] font-bold">월세 기준</span>
        </div>
        <p className="m-0 mt-1 text-[11px] leading-5 text-text-muted">보증금을 월세로 환산한 값입니다. 결과는 만원 단위로 절삭합니다.</p>
      </div>
      <p className="m-0 text-[11px] leading-5 text-text-muted">기본 전환율은 {rateLoading ? '불러오는 중입니다' : rateSource + ' 기준입니다'}. 사용자가 직접 바꿔서 계산할 수 있습니다.</p>
    </div>
  );
}

function NumberField({ label, value, onChange, step = 1 }: { label: string; value: number; onChange: (value: number) => void; step?: number }) {
  return (
    <label className="grid gap-1 text-[11px] font-bold text-text-muted">
      {label}
      <input
        type="number"
        min={0}
        step={step}
        value={Number.isFinite(value) ? value : 0}
        onChange={(event) => onChange(Number(event.target.value || 0))}
        className="h-9 rounded-[9px] border border-border bg-white px-2 text-[12px] font-semibold text-text outline-none focus:border-[var(--color-heatmap-2)]"
      />
    </label>
  );
}

function RealEstateListingAnalysis({
  address,
  deposit,
  monthlyRent,
  convertedRent,
  onAddressChange,
  onDepositChange,
  onMonthlyRentChange,
}: {
  address: string;
  deposit: number;
  monthlyRent: number;
  convertedRent: number;
  onAddressChange: (value: string) => void;
  onDepositChange: (value: number) => void;
  onMonthlyRentChange: (value: number) => void;
}) {
  return (
    <div className="grid gap-3">
      <div className="grid gap-2 rounded-card border border-border bg-white p-3">
        <label className="grid gap-1 text-[11px] font-bold text-text-muted">
          매물 주소
          <input
            value={address}
            onChange={(event) => onAddressChange(event.target.value)}
            className="h-9 rounded-[9px] border border-border bg-white px-2 text-[12px] font-semibold text-text outline-none focus:border-[var(--color-heatmap-2)]"
          />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <NumberField label="보증금" value={deposit} onChange={onDepositChange} step={100} />
          <NumberField label="월세" value={monthlyRent} onChange={onMonthlyRentChange} step={5} />
        </div>
        <button type="button" className="h-9 rounded-[10px] bg-[var(--color-heatmap-5)] text-[12px] font-bold text-white">실거래 기반 가격 분석</button>
      </div>
      <div className="grid gap-2 rounded-card border border-border bg-white p-3">
        <div className="rounded-card border border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] p-3">
          <span className="block text-[11px] font-bold text-text-muted">입력 매물 환산월세</span>
          <strong className="mt-1 block text-[34px] leading-none text-[var(--color-heatmap-5)]">{convertedRent}</strong>
        </div>
        <ul className="m-0 grid gap-1.5 p-0 text-[12px] text-text-muted">
          <li className="flex justify-between gap-3 rounded-[9px] bg-surface-alt px-2.5 py-2"><span>비교 데이터</span><b className="text-text">국토교통부 실거래가</b></li>
          <li className="flex justify-between gap-3 rounded-[9px] bg-surface-alt px-2.5 py-2"><span>비교 방식</span><b className="text-text">해당 법정동</b></li>
        </ul>
      </div>
      <p className="m-0 text-[11px] leading-5 text-text-muted">현재 화면은 입력 UI입니다. 실제 비교 결과는 추후 실거래 DB 분석 API와 연결할 때 채워집니다.</p>
    </div>
  );
}

function RealEstateLinks() {
  return (
    <div className="grid gap-3">
      <LinkGroup title="매물·시세 확인" caption="가격 비교" links={[
        ['RT', '국토교통부 실거래가', '주변 시세와 최근 거래 확인', 'https://rt.molit.go.kr/'],
        ['N', '네이버페이 부동산', '지도 기반 매물과 지역 정보 확인', 'https://fin.land.naver.com/home'],
        ['KB', 'KB부동산', '시세, 단지, 지역 가격 흐름 참고', 'https://kbland.kr/'],
        ['REB', '한국부동산원', '부동산테크, R-ONE 등 공식 통계 연결', 'https://www.kab.co.kr/'],
        ['직', '직방', '외부 매물 탐색', 'https://www.zigbang.com/'],
        ['다', '다방', '외부 매물 탐색', 'https://www.dabangapp.com/'],
      ]} />
      <LinkGroup title="등기·서류 확인" caption="권리관계" links={[
        ['등', '인터넷등기소', '등기부등본 권리관계 확인', 'https://www.iros.go.kr/'],
        ['24', '정부24', '건축물대장, 주민등록 등 민원 확인', 'https://www.gov.kr/'],
        ['서울', '서울부동산정보광장', '서울 부동산 정보와 중개업소 확인', 'https://land.seoul.go.kr:444/'],
      ]} />
      <LinkGroup title="보증·상담" caption="피해 예방" links={[
        ['HUG', 'HUG 주택도시보증공사', '보증 가능 여부와 임대인 조회', 'https://www.khug.or.kr/'],
        ['상담', '서울주거포털 전세사기 예방', '전월세종합지원센터와 예방 자료', 'https://housing.seoul.go.kr/site/main/content/sh05_070200'],
        ['안전', '국토교통부 안전한 집', '전세사기 예방 체크리스트와 셀프 테스트', 'https://www.molit.go.kr/2023safehome/main.jsp'],
      ]} />
    </div>
  );
}

function LinkGroup({
  title,
  caption,
  links,
}: {
  title: string;
  caption: string;
  links: Array<[string, string, string, string]>;
}) {
  return (
    <section className="grid gap-1.5">
      <h3 className="m-0 flex items-center justify-between text-[12px] font-bold text-[var(--color-heatmap-5)]">
        {title}
        <span className="text-[10px] font-semibold text-text-muted">{caption}</span>
      </h3>
      {links.map(([logo, titleText, description, href]) => (
        <a key={href} href={href} target="_blank" rel="noreferrer" className="grid min-h-14 grid-cols-[34px_1fr_auto] items-center gap-2 rounded-card border border-border bg-white p-2.5 text-text no-underline transition hover:border-[var(--color-heatmap-2)] hover:bg-[var(--color-heatmap-1)]">
          <span className="inline-flex h-[34px] w-[34px] items-center justify-center rounded-[10px] bg-surface-alt text-[11px] font-bold text-[var(--color-heatmap-5)]">{logo}</span>
          <span className="min-w-0">
            <span className="block truncate text-[13px] font-bold">{titleText}</span>
            <span className="mt-0.5 block truncate text-[11px] text-text-muted">{description}</span>
          </span>
          <span aria-hidden="true" className="text-text-muted">↗</span>
        </a>
      ))}
    </section>
  );
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
      className={`pointer-events-none relative z-0 w-[var(--map-control-width)] rounded-card border border-border/70 bg-[var(--map-guide-bg)] px-3 py-2.5 text-left shadow-lg backdrop-blur ${className}`}
      aria-label={`${title} 안내`}
    >
      <strong className="block text-[13px] font-semibold text-text">{title}</strong>
      <p className="m-0 mt-1 whitespace-normal break-keep text-[12px] leading-[1.45] text-text-muted">{children}</p>
    </aside>
  );
}

function IconTooltip({ children }: { children: React.ReactNode }) {
  return (
    <span className="pointer-events-none absolute bottom-[calc(100%+8px)] left-1/2 z-[1300] hidden -translate-x-1/2 whitespace-nowrap rounded-[6px] border border-border bg-white/95 px-2 py-1 text-[12px] font-semibold text-text shadow-lg group-hover:block group-focus-within:block">
      {children}
    </span>
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
  disabled = false,
}: {
  id: string;
  label: string;
  active?: boolean;
  open: boolean;
  onToggle: (id: string) => void;
  onClose?: () => void;
  children: React.ReactNode;
  width?: string;
  disabled?: boolean;
}) {
  return (
    <div className={`relative min-w-0 ${open ? 'z-[1300]' : 'z-[600]'} ${width}`}>
      <button
        type="button"
        onClick={() => { if (!disabled) onToggle(id); }}
        disabled={disabled}
        className={`flex h-9 w-full min-w-0 items-center justify-between overflow-hidden rounded-[var(--map-control-radius)] border px-3 text-[13px] font-semibold shadow-sm transition ${
          active ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'border-border bg-white/95 text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
        } ${disabled ? 'cursor-not-allowed opacity-45 hover:bg-white/95 hover:text-text' : ''}`}
        aria-expanded={open}
      >
        <span className="block min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-left" title={label}>{label}</span>
        <span className="ml-2 shrink-0 text-[14px] leading-none" aria-hidden="true">▾</span>
      </button>
      {open ? (
        <div className="absolute left-[calc(100%+8px)] top-0 z-[1400] w-[300px] rounded-[8px] border border-border bg-white p-3 shadow-xl">
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
  step = 1,
}: {
  title: string;
  unit: string;
  min: number;
  max: number;
  onChange: (min: number, max: number) => void;
  presets: Array<{ label: string; min: number; max: number }>;
  step?: number;
}) {
  return (
    <div className="grid gap-3">
      <h3 className="m-0 text-[14px] font-semibold text-text">{title}</h3>
      <div className="flex items-end gap-2">
        <label className="min-w-0 flex-1 grid gap-1 text-[12px] font-semibold text-text-muted">
          최소 {unit}
          <input
            type="number"
            step={step}
            value={min}
            onChange={(e) => onChange(Number(e.target.value), max)}
            className="h-8 w-full min-w-0 rounded-[6px] border border-border bg-surface-alt px-2 text-[13px] text-text"
          />
        </label>
        <label className="min-w-0 flex-1 grid gap-1 text-[12px] font-semibold text-text-muted">
          최대 {unit}
          <input
            type="number"
            step={step}
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

function MapPopup({ popup, onClose, heatLayer, ranks, rankTotal }: { popup: SelectedPopup; onClose: () => void; heatLayer: ScoreLayerKey; ranks: ScoreRanks; rankTotal: number }) {
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
          <div className="grid grid-cols-2 gap-2">
            <Metric label="종합" value={adong.score} rank={ranks.composite[adong.code]} rankTotal={rankTotal} active={heatLayer === 'composite'} className="col-span-2" />
            <Metric label="부동산" value={adong.score_rent} rank={ranks.rent[adong.code]} rankTotal={rankTotal} active={heatLayer === 'rent'} />
            <Metric label="교통" value={adong.score_transit} rank={ranks.transit[adong.code]} rankTotal={rankTotal} active={heatLayer === 'transit'} />
            <Metric label="편의시설" value={adong.score_amenity} rank={ranks.amenity[adong.code]} rankTotal={rankTotal} active={heatLayer === 'amenity'} />
            <Metric label="안전" value={adong.score_safety} rank={ranks.safety[adong.code]} rankTotal={rankTotal} active={heatLayer === 'safety'} />
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
  if (popup.type === 'deal_loading') {
    return (
      <article className="absolute left-1/2 top-1/2 z-[550] w-[320px] -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-white p-4 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="m-0 text-[12px] font-semibold text-text-muted">거래 상세</p>
            <h2 className="m-0 text-[18px] font-semibold text-text">불러오는 중...</h2>
          </div>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
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

function Metric({ label, value, suffix = '', active = false, rank, rankTotal, className = '' }: { label: string; value: number | null | undefined; suffix?: string; active?: boolean; rank?: number; rankTotal?: number; className?: string }) {
  return (
    <div className={`rounded-card border p-3 ${active ? 'border-[var(--color-heatmap-4)] bg-[var(--color-heatmap-1)]' : 'border-border bg-surface-alt'} ${className}`}>
      <p className="m-0 text-[12px] font-semibold text-text-muted">{label}</p>
      <strong className="mt-1 block text-[20px] text-text">{typeof value === 'number' && Number.isFinite(value) ? Math.round(value) : '-'}{suffix}</strong>
      {rank && rankTotal ? <span className="mt-1 block text-[11px] font-semibold text-text-subtle">순위 {rank}/{rankTotal}</span> : null}
    </div>
  );
}

type ScoreRanks = Record<ScoreLayerKey, Record<string, number>>;

function buildScoreRanks(adongs: AdongScore[]): ScoreRanks {
  const rankBy = (pick: (d: AdongScore) => number | null | undefined) => {
    const safeScore = (d: AdongScore) => Number.isFinite(pick(d)) ? Number(pick(d)) : -Infinity;
    const result: Record<string, number> = {};
    adongs
      .filter((d) => Number.isFinite(pick(d)))
      .sort((a, b) => safeScore(b) - safeScore(a))
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
    safety: rankBy((d) => d.score_safety),
  };
}

export default function MainMap() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const [regionLevel, setRegionLevel] = useState<RegionLevel>('adong');
  const [mapMode, setMapMode] = useState<MapMode>(() => {
    const mode = searchParams.get('mode');
    return mode === 'plain' || mode === 'heatmap' || mode === 'realestate' || mode === 'facility' ? mode : 'heatmap';
  });
  const [heatLayer, setHeatLayer] = useState<ScoreLayerKey>('composite');
  const [facilityKeys, setFacilityKeys] = useState<Set<FacilityKey>>(
    () => new Set(),
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
  const [openDataSourcePanel, setOpenDataSourcePanel] = useState<DataSourcePanel>(null);
  const [realEstateHelperOpen, setRealEstateHelperOpen] = useState(false);
  const [locateRequest, setLocateRequest] = useState(0);
  const [homeRequest, setHomeRequest] = useState(0);
  const toastTimer = useRef<number | null>(null);

  const { filters, patch, reset } = useStudioMatchFilters();
  const adongScoresQuery = useAdongScores(DEFAULT_WEIGHTS);
  const ldongScoresQuery = useLdongScores(DEFAULT_WEIGHTS);
  const scoresData = regionLevel === 'ldong' ? (ldongScoresQuery.data ?? []) : (adongScoresQuery.data ?? []);
  const scoresLoading = regionLevel === 'ldong' ? ldongScoresQuery.isLoading : adongScoresQuery.isLoading;
  const scoresError = regionLevel === 'ldong' ? ldongScoresQuery.isError : adongScoresQuery.isError;
  const matchQuery = useAdongMatchCounts(filters, mapMode === 'realestate');
  const matchCounts = matchQuery.data?.adongs ?? [];

  const rentCacheQuery = useRentDealCache(mapMode === 'realestate');
  const filteredPins = useMemo(() => {
    return applyClientCacheFilter(rentCacheQuery.data, filters, mapState?.bbox ?? null);
  }, [rentCacheQuery.data, filters, mapState?.bbox]);

  const selectedFacilityCategories = useMemo(() => Array.from(facilityKeys), [facilityKeys]);
  const amenitiesQuery = useQuery({
    queryKey: ['amenities', 'bbox', mapState?.bbox, selectedFacilityCategories.join(',')],
    queryFn: () => getAmenitiesBbox({
      bbox: [
        mapState!.bbox.lng1,
        mapState!.bbox.lat1,
        mapState!.bbox.lng2,
        mapState!.bbox.lat2,
      ],
      categories: selectedFacilityCategories,
      limit: 800,
    }),
    enabled: mapMode === 'facility' && mapState != null && selectedFacilityCategories.length > 0,
    staleTime: 60_000,
  });

  const visibleAmenities = useMemo(() => {
    if (selectedFacilityCategories.length === 0) return [];
    const selected = new Set(selectedFacilityCategories);
    return (amenitiesQuery.data?.items ?? []).filter((item) => selected.has(item.category as FacilityKey));
  }, [amenitiesQuery.data?.items, selectedFacilityCategories]);

  const ranks = useMemo(() => buildScoreRanks(scoresData), [scoresData]);

  const selectedJibun = popup?.type === 'deal' ? popup.key : null;
  const heatmapActiveLayer: ScoreLayerKey = heatLayer;
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
    setRealEstateHelperOpen(false);
    const next = new URLSearchParams(searchParams);
    if (mode === 'heatmap') next.delete('mode');
    else next.set('mode', mode);
    setSearchParams(next, { replace: true });
  };

  const toggleDropdown = (id: string) => {
    setRealEstateHelperOpen(false);
    setOpenDropdown((prev) => (prev === id ? null : id));
  };

  const handlePinClick = (key: string, pin: RentDealCachePin | RentDealPin) => {
    setPopup({ type: 'deal_loading', key });
    getRentDealDetail(pin.id)
      .then((deal) => setPopup({ type: 'deal', key, pins: [deal] }))
      .catch(() => {
        setPopup(null);
        flash('거래 상세 정보를 불러오지 못했습니다.');
      });
  };

  const toggleFacility = (key: FacilityKey) => {
    setPopup(null);
    setFacilityKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleDashboardOpen = () => {
    setDashboardMiniMapTransitionTarget();
    setRouteTransition(true);
    window.setTimeout(() => navigate('/dashboard'), 360);
  };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      let handled = false;
      if (popup) {
        setPopup(null);
        handled = true;
      }
      if (searchResults.length > 0 || searchLoading) {
        setSearchResults([]);
        setSearchLoading(false);
        handled = true;
      }
      if (openDropdown) {
        setOpenDropdown(null);
        handled = true;
      }
      if (realEstateHelperOpen) {
        setRealEstateHelperOpen(false);
        handled = true;
      }
      if (openDataSourcePanel) {
        setOpenDataSourcePanel(null);
        handled = true;
      }
      if (handled) event.preventDefault();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [popup, searchResults.length, searchLoading, openDropdown, realEstateHelperOpen, openDataSourcePanel]);

  return (
    <main className="map-redesign relative h-screen w-screen overflow-hidden bg-bg text-text">
      <h1 className="sr-only">서울 주거 지도</h1>

      <HeatMap
        adongs={scoresData}
        activeLayer={heatmapActiveLayer}
        heatmapVisible={heatmapVisible}
        mode={heatmapMode}
        matchCounts={matchCounts}
        regionLevel={regionLevel}
        onAdongClick={mapMode === 'heatmap' ? (adong) => setPopup({ type: 'adong', adong }) : undefined}
      >
        <CurrentLocationLayer
          requestId={locateRequest}
          onError={(message) => flash(message)}
        />
        <HomeLocationLayer
          requestId={homeRequest}
          lat={user?.home_lat}
          lng={user?.home_lng}
          onError={(message) => flash(message)}
        />
        <SearchFlyTo item={selectedSearchItem} />
        {mapMode !== 'heatmap' ? (
          <HomeMarker lat={user?.home_lat} lng={user?.home_lng} />
        ) : null}
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
        {mapMode === 'facility' ? (
          <AmenityLayer
            items={visibleAmenities}
            onSelect={(item) => setPopup({
              type: 'facility',
              title: item.name,
              description: FACILITY_LABELS[item.category as FacilityKey] ?? item.category,
            })}
          />
        ) : null}
      </HeatMap>

      <section className="pointer-events-none absolute left-5 top-5 z-[500] grid justify-items-start gap-2" aria-label="지도 검색과 필터">
        <div className="pointer-events-auto relative">
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

        <div className="pointer-events-auto grid w-[var(--map-control-width)] grid-cols-4 rounded-card border border-border bg-white/95 p-1 shadow-lg backdrop-blur" role="group" aria-label="지도 모드">
          <SegmentButton active={mapMode === 'plain'} onClick={() => handleModeChange('plain')}>지도</SegmentButton>
          <SegmentButton active={mapMode === 'heatmap'} onClick={() => handleModeChange('heatmap')}>히트맵</SegmentButton>
          <SegmentButton active={mapMode === 'realestate'} onClick={() => handleModeChange('realestate')}>부동산</SegmentButton>
          <SegmentButton active={mapMode === 'facility'} onClick={() => handleModeChange('facility')}>시설</SegmentButton>
        </div>


        {mapMode === 'heatmap' ? (
          <div className="pointer-events-auto relative z-[600] w-[152px] rounded-card border border-border bg-white/95 p-2 shadow-lg backdrop-blur">
            <div className="mb-2 grid w-full grid-cols-2 rounded-[12px] border border-[var(--color-heatmap-2)] bg-white/80 p-1" role="group" aria-label="지역 단위">
              <button type="button" onClick={() => setRegionLevel('adong')} className={`h-8 rounded-[9px] px-3 text-[13px] font-semibold transition ${regionLevel === 'adong' ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm' : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}>행정동</button>
              <button type="button" onClick={() => setRegionLevel('ldong')} className={`h-8 rounded-[9px] px-3 text-[13px] font-semibold transition ${regionLevel === 'ldong' ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm' : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}>법정동</button>
            </div>
            <div className="grid w-full gap-1.5">
              {HEAT_LAYERS.map((layer) => (
                <div key={layer.key} className="group relative">
                  <button
                    type="button"
                    onClick={() => {
                      setHeatLayer(layer.key);
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

        {mapMode === 'realestate' ? (
          <div className="pointer-events-none flex items-start gap-2">
            <div className="pointer-events-auto relative z-[600] grid w-[152px] min-w-[152px] max-w-[152px] gap-2 rounded-card border border-border bg-white/95 p-2 shadow-lg backdrop-blur">
            <div className="grid grid-cols-2 gap-1 rounded-[var(--map-control-radius)] border border-border bg-surface-alt p-1">
              <button
                type="button"
                onClick={() => patch({ filter_mode: 'converted' })}
                className={`h-8 rounded-[6px] text-[12px] font-semibold ${filters.filter_mode === 'converted' ? 'bg-white text-text shadow-sm' : 'text-text-muted'}`}
              >
                환산
              </button>
              <button
                type="button"
                onClick={() => patch({ filter_mode: 'raw' })}
                className={`h-8 rounded-[6px] text-[12px] font-semibold ${filters.filter_mode === 'raw' ? 'bg-white text-text shadow-sm' : 'text-text-muted'}`}
              >
                보증/월세
              </button>
            </div>
            <DropdownButton id="period" label={PERIOD_LABELS[filters.period]} active width="w-full" open={openDropdown === 'period'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <ChoiceList
                selected={filters.period}
                onSelect={(value) => { patch({ period: value as ExplorePeriod }); setOpenDropdown(null); }}
                items={Object.entries(PERIOD_LABELS).map(([value, label]) => ({ value, label }))}
              />
            </DropdownButton>
            <DropdownButton id="deal-type" label={formatDealTypes(filters.deal_types)} active width="w-full max-w-full" open={openDropdown === 'deal-type'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <div className="grid gap-2">
                <h3 className="m-0 pr-8 text-[14px] font-semibold text-text">유형 선택</h3>
                <div className="flex flex-wrap gap-1.5">
                {DEAL_TYPE_FILTER_OPTIONS.map((type) => {
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
              </div>
            </DropdownButton>
            <DropdownButton id="deposit" label={formatRangeLabel('보증금', filters.deposit_min, filters.deposit_max, RANGE_ALL.deposit.max)} width="w-full" open={openDropdown === 'deposit'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)} disabled={filters.filter_mode === 'converted'}>
              <RangePanel
                title="보증금 범위"
                unit="만원"
                min={filters.deposit_min}
                max={filters.deposit_max}
                onChange={(deposit_min, deposit_max) => patch({ deposit_min, deposit_max })}
                step={100}
                presets={[{ label: '전체', min: RANGE_ALL.deposit.min, max: RANGE_ALL.deposit.max }, { label: '3천 이하', min: 0, max: 3000 }, { label: '5천 이하', min: 0, max: 5000 }, { label: '1억 이하', min: 0, max: 10000 }]}
              />
            </DropdownButton>
            <DropdownButton id="monthly" label={formatRangeLabel('월세', filters.monthly_min, filters.monthly_max, RANGE_ALL.monthly.max)} width="w-full" open={openDropdown === 'monthly'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)} disabled={filters.filter_mode === 'converted'}>
              <RangePanel
                title="월세 범위"
                unit="만원"
                min={filters.monthly_min}
                max={filters.monthly_max}
                onChange={(monthly_min, monthly_max) => patch({ monthly_min, monthly_max })}
                step={5}
                presets={[{ label: '전체', min: RANGE_ALL.monthly.min, max: RANGE_ALL.monthly.max }, { label: '50 이하', min: 0, max: 50 }, { label: '80 이하', min: 0, max: 80 }, { label: '120 이하', min: 0, max: 120 }]}
              />
            </DropdownButton>
            <DropdownButton id="converted" label={formatRangeLabel('환산월세', filters.converted_min, filters.converted_max, RANGE_ALL.converted.max)} width="w-full" open={openDropdown === 'converted'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)} disabled={filters.filter_mode === 'raw'}>
              <RangePanel
                title="환산월세 범위"
                unit="만원"
                min={filters.converted_min}
                max={filters.converted_max}
                onChange={(converted_min, converted_max) => patch({ converted_min, converted_max })}
                step={5}
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
            <RealEstateHelperPanel open={realEstateHelperOpen} onToggle={() => { setOpenDropdown(null); setRealEstateHelperOpen((prev) => !prev); }} />
          </div>
        ) : null}

        {mapMode === 'facility' ? (
          <div className="pointer-events-auto relative z-[600] grid max-h-[460px] w-[152px] justify-items-start gap-1.5 overflow-y-auto rounded-card border border-border bg-white/95 p-2 shadow-lg backdrop-blur">
            {FACILITY_ORDER.map((key) => (
              <FilterButton key={key} active={facilityKeys.has(key)} onClick={() => toggleFacility(key)} className="w-full">
                <span className="inline-flex items-center gap-1.5">
                  <span aria-hidden="true" className="inline-flex h-4 w-4 items-center justify-center" dangerouslySetInnerHTML={{ __html: FACILITY_ICONS[key] }} />
                  <span>{FACILITY_LABELS[key]}</span>
                </span>
              </FilterButton>
            ))}
            <ResetButton onClick={() => { setPopup(null); setFacilityKeys(new Set()); }}>초기화</ResetButton>
          </div>
        ) : null}

        {mapMode === 'plain' ? (
          <ModeGuide title="지도">
            기본 지도를 표시합니다. 검색한 지역이나 지점을 중심으로 지도를 탐색할 수 있습니다.
          </ModeGuide>
        ) : null}
        {mapMode === 'heatmap' ? (
          <ModeGuide title="히트맵">
            선택한 점수를 기준으로 {regionLevel === 'adong' ? '행정동별' : '법정동별'} 분포를 색으로 보여줍니다. 동을 클릭하면 주요 점수와 순위를 확인할 수 있습니다.
          </ModeGuide>
        ) : null}
        {mapMode === 'realestate' ? (
          <ModeGuide title="부동산">
            선택한 조건에 맞는 거래 내역을 지도에 표시합니다. 지도를 확대하면 개별 거래 위치를 확인할 수 있습니다.
          </ModeGuide>
        ) : null}
        {mapMode === 'facility' ? (
          <ModeGuide title="시설">
            선택한 시설을 지도 위에 표시합니다. 지도를 확대하면 주변 시설 위치를 더 자세히 확인할 수 있습니다.
          </ModeGuide>
        ) : null}
      </section>

      <div className="fixed right-6 top-6 z-[1200] grid justify-items-end gap-1.5">
        <Link
          to={user ? '/mypage' : '/login'}
          className="app-floating-button h-10 min-h-10"
        >
          {user ? '마이페이지' : '로그인'}
        </Link>
        <div className="grid translate-x-[-10px] justify-items-end gap-0.5 text-[11px] font-semibold leading-4 text-text">
          <button type="button" className="bg-transparent p-0 hover:text-text" onClick={() => setOpenDataSourcePanel('terms')}>이용약관</button>
          <button type="button" className="bg-transparent p-0 hover:text-text" onClick={() => setOpenDataSourcePanel('privacy')}>개인정보처리방침</button>
          <button type="button" className="bg-transparent p-0 hover:text-text" onClick={() => setOpenDataSourcePanel('data')}>데이터 출처</button>
        </div>
        {openDataSourcePanel ? <LegalPanel panel={openDataSourcePanel} onClose={() => setOpenDataSourcePanel(null)} /> : null}
      </div>

      <div className="absolute bottom-6 left-6 z-[500] flex items-center gap-2">
        <button
          type="button"
          onClick={handleDashboardOpen}
          className="app-floating-button"
        >
          대시보드 보기
        </button>
        <span className="group relative inline-flex">
        <button
          type="button"
          onClick={() => setLocateRequest((v) => v + 1)}
          aria-label="현재 위치로 이동"
          title="현재 위치로 이동"
          className="map-icon-button border-border/60 bg-white/55 shadow-sm backdrop-blur hover:bg-white/80"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="6.5" />
            <circle cx="12" cy="12" r="1.8" fill="currentColor" stroke="none" />
            <path d="M12 2.75v3M12 18.25v3M2.75 12h3M18.25 12h3" />
          </svg>
        </button>
        <IconTooltip>현재위치로 이동</IconTooltip>
        </span>
        <span className="group relative inline-flex">
        <button
          type="button"
          aria-label="집으로 이동"
          title="집으로 이동"
          onClick={() => {
            if (!user) {
              flash('로그인 후 집 위치로 이동할 수 있습니다.');
              return;
            }
            setHomeRequest((v) => v + 1);
          }}
          className="map-icon-button border-border/60 bg-white/55 shadow-sm backdrop-blur hover:bg-white/80"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 10.75 12 4l8 6.75" />
            <path d="M6.5 9.75V20h11V9.75" />
            <path d="M10 20v-5.5h4V20" />
          </svg>
        </button>
        <IconTooltip>집으로 이동</IconTooltip>
        </span>
      </div>
      {mapMode === 'heatmap' ? (
        <div className="absolute bottom-6 left-1/2 z-[440] flex -translate-x-1/2 items-center gap-3 rounded-card border border-border bg-white/95 px-4 py-2 text-[13px] font-semibold text-text shadow-lg backdrop-blur">
          <span>낮음</span>
          <div className="flex h-3 w-[180px] overflow-hidden rounded-full border border-border/50" aria-label="히트맵 5단계 범례">
            {HEATMAP_COLORS_ORDERED.map((color, index) => (
              <span key={`${color}-${index}`} className="h-full flex-1" style={{ backgroundColor: color }} />
            ))}
          </div>
          <span>높음</span>
          <strong className="text-[var(--color-heatmap-5)]">{HEAT_LAYERS.find((l) => l.key === heatLayer)?.label}</strong>
        </div>
      ) : null}

      {scoresLoading ? <StatusPill>지도 데이터를 불러오는 중입니다.</StatusPill> : null}
      {scoresError ? <StatusPill tone="danger">지도 데이터를 불러오지 못했습니다.</StatusPill> : null}
      {mapMode === 'realestate' && matchQuery.isFetching ? <StatusPill>부동산 데이터를 불러오는 중입니다.</StatusPill> : null}
      {mapMode === 'facility' && amenitiesQuery.isFetching ? <StatusPill>시설 데이터를 불러오는 중입니다.</StatusPill> : null}
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

function AmenityLayer({ items, onSelect }: { items: AmenityBboxItem[]; onSelect: (item: AmenityBboxItem) => void }) {
  return (
    <>
      {items.map((item) => {
        if (typeof item.lat !== 'number' || typeof item.lng !== 'number') return null;
        const key = item.category as FacilityKey;
        const iconText = FACILITY_ICONS[key] ?? '•';
        const icon = L.divIcon({
          className: 'amenity-pin-icon',
          html: `<span style="display:flex;width:28px;height:28px;align-items:center;justify-content:center;border:1px solid rgba(20,83,45,.32);border-radius:999px;background:rgba(255,255,255,.94);box-shadow:0 2px 10px rgba(15,23,42,.22);font-size:15px;font-weight:800;line-height:1;color:#14532d;">${iconText}</span>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });
        const itemKey = `${item.source_table}-${item.source_id}`;
        return [
            <Marker key={`${itemKey}-icon`} position={[item.lat, item.lng]} icon={icon} interactive={false} />,
            <CircleMarker
              key={`${itemKey}-hit`}
              center={[item.lat, item.lng]}
              radius={16}
              pathOptions={{
                color: 'transparent',
                weight: 0,
                fillColor: '#22c55e',
                fillOpacity: 0.01,
              }}
              eventHandlers={{
                click: (event) => {
                  event.originalEvent.stopPropagation();
                  onSelect(item);
                },
              }}
            />
        ];
      })}
    </>
  );
}

function HomeMarker({ lat, lng }: { lat?: number | null; lng?: number | null }) {
  const icon = useMemo(() => L.divIcon({
    className: 'home-marker-icon',
    html: `<span style="display:flex;width:34px;height:34px;align-items:center;justify-content:center;border:2px solid rgba(126,34,206,.9);border-radius:999px;background:rgba(250,245,255,.96);box-shadow:0 8px 18px rgba(88,28,135,.28);color:#7e22ce;"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 10.75 12 4l8 6.75"/><path d="M6.5 9.75V20h11V9.75"/><path d="M10 20v-5.5h4V20"/></svg></span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  }), []);

  if (typeof lat !== 'number' || typeof lng !== 'number' || !Number.isFinite(lat) || !Number.isFinite(lng)) {
    return null;
  }

  return <Marker position={[lat, lng]} icon={icon} interactive={false} zIndexOffset={900} />;
}

function LegalPanel({ panel, onClose }: { panel: Exclude<DataSourcePanel, null>; onClose: () => void }) {
  const title = panel === 'terms' ? '이용약관' : panel === 'privacy' ? '개인정보처리방침' : '데이터 출처';
  return (
    <aside className="absolute right-0 top-[calc(100%+8px)] w-[340px] rounded-card border border-border/70 bg-[var(--map-guide-bg)] p-4 text-[12px] leading-5 text-text shadow-xl backdrop-blur" aria-label={title}>
      <div className="flex items-start justify-between gap-3">
        <strong className="text-[13px] text-text">{title}</strong>
        <button type="button" onClick={onClose} className="h-7 w-7 rounded-[6px] bg-surface-alt text-[16px] text-text-muted">×</button>
      </div>
      {panel === 'terms' ? (
        <p className="m-0 mt-3 text-text-muted">서비스는 공공데이터 기반 주거 탐색 정보를 제공합니다. 데이터의 최신성·정확성은 원천 제공기관과 갱신 시점에 따라 달라질 수 있으며, 사용자는 이를 참고 정보로 활용합니다.</p>
      ) : null}
      {panel === 'privacy' ? (
        <p className="m-0 mt-3 text-text-muted">회원 정보, 선택 입력 주소, 집 위치 좌표, 암호화된 AI API KEY를 서비스 제공 목적으로 처리합니다. AI API KEY는 사용자의 복호화 문구 없이는 서버 단독으로 사용할 수 없고, 7일 이상 로그인 기록이 없으면 삭제됩니다.</p>
      ) : null}
      {panel === 'data' ? (
        <ul className="mt-3 grid gap-1 pl-4 text-text-muted">
          <li>지도 타일·주소 검색·좌표 변환: V-World</li>
          <li>행정동/법정동 경계: V-World 행정구역 경계 데이터</li>
          <li>실거래·상권·대중교통 등: 공공데이터포털, 서울 열린데이터광장</li>
          <li>안전 지표·전월세전환율: KOSIS 기반</li>
        </ul>
      ) : null}
    </aside>
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

function HomeLocationLayer({
  requestId,
  lat,
  lng,
  onError,
}: {
  requestId: number;
  lat?: number | null;
  lng?: number | null;
  onError: (message: string) => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (requestId === 0) return;
    if (typeof lat !== 'number' || typeof lng !== 'number' || !Number.isFinite(lat) || !Number.isFinite(lng)) {
      onError('집 주소 좌표가 없습니다. 마이페이지에서 주소를 확인해주세요.');
      return;
    }
    map.flyTo([lat, lng], Math.max(map.getZoom(), 15), { duration: 0.6 });
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
