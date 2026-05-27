// /adong/:slug/explore — 자취 시세 BI 대시보드 (Phase 4.8).
import { Link, useParams } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';

import { CHART_COLORS } from '@/lib/colors';
import { usePageTitle } from '@/contexts/PageTitleContext';
import {
  DEFAULT_EXPLORE_FILTERS,
  useAdongExplore,
  useExploreFilters,
} from '@/hooks/useAdongExplore';
import type {
  ExploreDealType,
  ExploreFilters,
  ExplorePeriod,
  ExploreSort,
} from '@/types/api';

const DEAL_TYPE_OPTIONS: Array<{ value: ExploreDealType; label: string }> = [
  { value: 'villa', label: '연립다세대' },
  { value: 'dagagu', label: '다가구' },
  { value: 'danok', label: '단독' },
  { value: 'officetel', label: '오피스텔' },
  { value: 'apt', label: '아파트' },
];

const PERIOD_OPTIONS: Array<{ value: ExplorePeriod; label: string }> = [
  { value: '3m', label: '3개월' },
  { value: '6m', label: '6개월' },
  { value: '12m', label: '12개월' },
  { value: '24m', label: '24개월' },
  { value: 'all', label: '전체' },
];

const DEAL_TYPE_FILL: Record<ExploreDealType, string> = {
  villa: CHART_COLORS.villa,
  dagagu: CHART_COLORS.dagagu,
  danok: CHART_COLORS.danok,
  officetel: CHART_COLORS.officetel,
  apt: CHART_COLORS.apt,
};

const SORT_OPTIONS: Array<{ value: ExploreSort; label: string }> = [
  { value: 'date_desc', label: '최신순' },
  { value: 'date_asc', label: '오래된순' },
  { value: 'converted_desc', label: '환산월세 높은순' },
  { value: 'converted_asc', label: '환산월세 낮은순' },
  { value: 'deposit_desc', label: '보증금 높은순' },
  { value: 'deposit_asc', label: '보증금 낮은순' },
  { value: 'monthly_desc', label: '월세 높은순' },
  { value: 'monthly_asc', label: '월세 낮은순' },
  { value: 'area_desc', label: '넓은순' },
  { value: 'area_asc', label: '좁은순' },
];

export default function AdongExplore() {
  const { slug } = useParams<{ slug: string }>();
  const { filters, patch, setPage, reset } = useExploreFilters();
  const { data, isLoading, isError, error } = useAdongExplore(slug, filters);

  usePageTitle(
    data ? `${data.adong.gu} ${data.adong.name} · 자취 시세 탐색` : '자취 시세 탐색',
  );

  if (!slug) {
    return <div className="p-12 text-center text-text-muted">잘못된 URL입니다.</div>;
  }
  if (isError) {
    return (
      <div className="p-12 text-center text-text-muted">
        데이터를 불러오지 못했습니다. {(error as Error)?.message}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-[280px_minmax(0,1fr)] gap-8 py-8 px-10 max-w-[1480px] mx-auto items-start">
      <ExploreSidebar filters={filters} patch={patch} reset={reset} />

      <main className="flex flex-col gap-9 min-w-0" aria-busy={isLoading}>
        <header className="flex flex-col gap-3 mb-2">
          <Link to={`/adong/${slug}`} className="no-underline text-text-subtle self-start mono-label hover:text-text">
            ← 동 상세로
          </Link>
          <h1 className="text-[28px] font-semibold m-0">
            {data ? `${data.adong.gu} ${data.adong.name}` : '...'}{' '}
            <span className="text-body-base font-normal text-text-subtle">자취 시세 탐색</span>
          </h1>
          <p className="m-0 text-text-muted mono-label">
            아래 필터를 조절하면 KPI · 차트 · 거래표가 모두 즉시 갱신됩니다
          </p>
        </header>

        {data ? (
          <>
            <KpiBlock kpi={data.kpi} />
            <ScatterBlock data={data.scatter} />
            <ChartsRow
              typeAvg={data.type_avg}
              depositBand={data.deposit_band}
              trend={data.monthly_trend}
            />
            <DealsBlock
              deals={data.deals}
              sort={filters.sort}
              onSortChange={(sort) => patch({ sort })}
              onPageChange={setPage}
            />
          </>
        ) : (
          <div className="p-12 text-center text-text-muted mono-label">불러오는 중...</div>
        )}
      </main>
    </div>
  );
}

interface SidebarProps {
  filters: ExploreFilters;
  patch: (delta: Partial<ExploreFilters>) => void;
  reset: () => void;
}

function ExploreSidebar({ filters, patch, reset }: SidebarProps) {
  const toggleType = (t: ExploreDealType) => {
    const has = filters.deal_types.includes(t);
    const next = has
      ? filters.deal_types.filter((x) => x !== t)
      : [...filters.deal_types, t];
    if (next.length === 0) return;
    patch({ deal_types: next });
  };

  const isDirty =
    JSON.stringify({ ...filters, page: 1 }) !==
    JSON.stringify({ ...DEFAULT_EXPLORE_FILTERS, page: 1 });

  return (
    <aside className="sticky top-6 flex flex-col gap-7 p-6 border border-divider rounded-md bg-surface max-h-[calc(100vh-48px)] overflow-y-auto" aria-label="필터 패널">
      <div className="flex justify-between items-center pb-3 border-b border-divider">
        <p className="mono-label m-0 text-text-subtle">FILTERS</p>
        {isDirty ? (
          <button type="button" className="bg-transparent border-0 text-text-subtle text-caption cursor-pointer py-1 px-2 rounded-sm hover:bg-surface-alt hover:text-text" onClick={reset}>
            초기화
          </button>
        ) : null}
      </div>

      <fieldset className="border-0 p-0 m-0 flex flex-col gap-2">
        <legend className="text-body-base font-medium text-text flex justify-between items-baseline">거래 유형</legend>
        <div className="flex flex-wrap gap-2">
          {DEAL_TYPE_OPTIONS.map((opt) => {
            const active = filters.deal_types.includes(opt.value);
            return (
              <button
                key={opt.value}
                type="button"
                className={`min-h-[44px] py-2 px-4 border rounded-full text-caption cursor-pointer transition-all duration-[120ms] ease-out ${
                  active
                    ? 'bg-surface-alt border-text text-text font-medium'
                    : 'bg-surface border-divider text-text-subtle hover:border-text-subtle hover:text-text hover:bg-surface-alt'
                }`}
                onClick={() => toggleType(opt.value)}
                aria-pressed={active}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
        <p className="text-caption text-text-muted m-0">
          아파트 포함하려면 클릭. 자취 4종은 기본 활성.
        </p>
      </fieldset>

      <fieldset className="border-0 p-0 m-0 flex flex-col gap-2">
        <legend className="text-body-base font-medium text-text flex justify-between items-baseline">기간</legend>
        <div className="grid grid-cols-3 gap-1">
          {PERIOD_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className={`flex items-center justify-center py-2 border rounded-sm text-caption cursor-pointer ${
                filters.period === opt.value
                  ? 'bg-text text-surface border-text'
                  : 'border-divider text-text-subtle hover:border-text-subtle'
              }`}
            >
              <input
                type="radio"
                name="period"
                value={opt.value}
                checked={filters.period === opt.value}
                onChange={() => patch({ period: opt.value })}
                className="hidden"
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <RangeField
        title="보증금 (만원)"
        min={0}
        max={50000}
        step={500}
        valueMin={filters.deposit_min}
        valueMax={filters.deposit_max}
        onChange={(lo, hi) => patch({ deposit_min: lo, deposit_max: hi })}
        formatter={(v) => v.toLocaleString()}
      />
      <RangeField
        title="월세 (만원)"
        min={0}
        max={300}
        step={5}
        valueMin={filters.monthly_min}
        valueMax={filters.monthly_max}
        onChange={(lo, hi) => patch({ monthly_min: lo, monthly_max: hi })}
        formatter={(v) => String(v)}
      />
      <RangeField
        title="면적 (m²)"
        min={0}
        max={150}
        step={1}
        valueMin={filters.area_min}
        valueMax={filters.area_max}
        onChange={(lo, hi) => patch({ area_min: lo, area_max: hi })}
        formatter={(v) => String(v)}
      />
    </aside>
  );
}

interface RangeFieldProps {
  title: string;
  min: number;
  max: number;
  step: number;
  valueMin: number;
  valueMax: number;
  onChange: (lo: number, hi: number) => void;
  formatter: (v: number) => string;
}

function RangeField({
  title,
  min,
  max,
  step,
  valueMin,
  valueMax,
  onChange,
  formatter,
}: RangeFieldProps) {
  return (
    <fieldset className="border-0 p-0 m-0 flex flex-col gap-2">
      <legend className="text-body-base font-medium text-text flex justify-between items-baseline">
        <span>{title}</span>
        <span className="text-caption text-text-subtle font-normal tabular">
          {formatter(valueMin)} ~ {formatter(valueMax)}
        </span>
      </legend>
      <div className="flex flex-col gap-2">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={valueMin}
          onChange={(e) => {
            const v = Number(e.target.value);
            onChange(Math.min(v, valueMax - step), valueMax);
          }}
          aria-label={`${title} 최솟값`}
          className="w-full h-6 bg-transparent cursor-pointer appearance-none [&::-webkit-slider-runnable-track]:h-1 [&::-webkit-slider-runnable-track]:rounded-[2px] [&::-webkit-slider-runnable-track]:bg-divider [&::-moz-range-track]:h-1 [&::-moz-range-track]:rounded-[2px] [&::-moz-range-track]:bg-divider [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-[18px] [&::-webkit-slider-thumb]:h-[18px] [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-text [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-surface [&::-webkit-slider-thumb]:shadow-[0_0_0_1px_var(--color-text)] [&::-webkit-slider-thumb]:-mt-[7px] [&::-webkit-slider-thumb]:cursor-grab [&::-moz-range-thumb]:w-[18px] [&::-moz-range-thumb]:h-[18px] [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-text [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-surface [&::-moz-range-thumb]:shadow-[0_0_0_1px_var(--color-text)] [&::-moz-range-thumb]:cursor-grab"
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={valueMax}
          onChange={(e) => {
            const v = Number(e.target.value);
            onChange(valueMin, Math.max(v, valueMin + step));
          }}
          aria-label={`${title} 최댓값`}
          className="w-full h-6 bg-transparent cursor-pointer appearance-none [&::-webkit-slider-runnable-track]:h-1 [&::-webkit-slider-runnable-track]:rounded-[2px] [&::-webkit-slider-runnable-track]:bg-divider [&::-moz-range-track]:h-1 [&::-moz-range-track]:rounded-[2px] [&::-moz-range-track]:bg-divider [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-[18px] [&::-webkit-slider-thumb]:h-[18px] [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-text [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-surface [&::-webkit-slider-thumb]:shadow-[0_0_0_1px_var(--color-text)] [&::-webkit-slider-thumb]:-mt-[7px] [&::-webkit-slider-thumb]:cursor-grab [&::-moz-range-thumb]:w-[18px] [&::-moz-range-thumb]:h-[18px] [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-text [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-surface [&::-moz-range-thumb]:shadow-[0_0_0_1px_var(--color-text)] [&::-moz-range-thumb]:cursor-grab"
        />
      </div>
    </fieldset>
  );
}

interface KpiBlockProps {
  kpi: { count: number; avg_converted_rent: number | null; min_deposit: number | null; avg_area_m2: number | null };
}

function KpiBlock({ kpi }: KpiBlockProps) {
  return (
    <div className="grid grid-cols-4 gap-5">
      <KpiCard
        label="필터된 거래"
        value={kpi.count.toLocaleString()}
        hint="현재 필터 매칭 건수"
      />
      <KpiCard
        label="평균 환산월세"
        value={kpi.avg_converted_rent != null ? `${kpi.avg_converted_rent}만원` : '-'}
        hint="월세 + 보증금 × 0.005"
      />
      <KpiCard
        label="최저 보증금"
        value={kpi.min_deposit != null ? `${kpi.min_deposit.toLocaleString()}만원` : '-'}
        hint="가장 진입 부담 적은 매물"
      />
      <KpiCard
        label="평균 면적"
        value={kpi.avg_area_m2 != null ? `${kpi.avg_area_m2}m²` : '-'}
        hint={kpi.avg_area_m2 != null ? `약 ${(kpi.avg_area_m2 / 3.3058).toFixed(1)}평` : ''}
      />
    </div>
  );
}

function KpiCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="p-6 border border-divider rounded-md bg-surface flex flex-col gap-3">
      <p className="mono-label m-0 text-text-subtle">{label}</p>
      <p className="m-0 text-[28px] font-semibold leading-[1.1] tabular">{value}</p>
      {hint ? <p className="m-0 text-caption text-text-muted">{hint}</p> : null}
    </div>
  );
}

function ScatterBlock({
  data,
}: {
  data: Array<{ deal_type: ExploreDealType; area_m2: number; converted_rent: number }>;
}) {
  const byType: Record<ExploreDealType, Array<{ x: number; y: number }>> = {
    villa: [],
    dagagu: [],
    danok: [],
    officetel: [],
    apt: [],
  };
  for (const p of data) {
    byType[p.deal_type]?.push({ x: p.area_m2, y: p.converted_rent });
  }
  return (
    <div className="border border-divider rounded-md bg-surface py-7 px-7 pb-6" aria-label="면적 · 환산월세 산점도">
      <header className="flex flex-col gap-2 mb-5">
        <h2 className="m-0 text-[22px] font-semibold tracking-[-0.01em]">면적 · 환산월세 분포</h2>
        <p className="mono-label m-0 text-text-muted">
          점 1 = 거래 1건 (최대 500건). 색상 = 거래 유형
        </p>
      </header>
      <div className="h-[380px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
            <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              name="면적"
              stroke={CHART_COLORS.axis}
              tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
              tickFormatter={(v) => `${v}m²`}
              tickMargin={6}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="환산월세"
              stroke={CHART_COLORS.axis}
              tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
              tickFormatter={(v) => `${v}`}
              tickMargin={6}
              width={56}
            />
            <ZAxis range={[28, 28]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--font-caption-size)',
              }}
              formatter={(value, name) => {
                const v = typeof value === 'number' ? value : Number(value);
                const n = String(name);
                if (n === '면적') return [`${v}m²`, n] as [string, string];
                if (n === '환산월세')
                  return [`${v}만원`, n] as [string, string];
                return [`${v}`, n] as [string, string];
              }}
            />
            <Legend
              verticalAlign="top"
              height={28}
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 'var(--font-caption-size)' }}
            />
            {(['villa', 'dagagu', 'danok', 'officetel', 'apt'] as ExploreDealType[]).map((k) =>
              byType[k].length > 0 ? (
                <Scatter
                  key={k}
                  name={DEAL_TYPE_OPTIONS.find((o) => o.value === k)?.label ?? k}
                  data={byType[k]}
                  fill={DEAL_TYPE_FILL[k]}
                  fillOpacity={0.65}
                />
              ) : null,
            )}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

interface ChartsRowProps {
  typeAvg: Array<{ deal_type: ExploreDealType; label: string; avg_converted_rent: number | null; count: number }>;
  depositBand: Array<{ band: string; count: number; avg_monthly_rent: number }>;
  trend: Array<{ month: string; villa: number | null; dagagu: number | null; danok: number | null; officetel: number | null }>;
}

function ChartsRow({ typeAvg, depositBand, trend }: ChartsRowProps) {
  const typeData = typeAvg.map((t) => ({
    ...t,
    avg: t.avg_converted_rent ?? 0,
    has: t.avg_converted_rent !== null,
  }));
  const bandData = depositBand.map((b) => ({
    band: formatBand(b.band),
    monthly: b.avg_monthly_rent,
    count: b.count,
  }));

  return (
    <div className="grid grid-cols-3 gap-5">
      <div className="border border-divider rounded-md bg-surface p-6 flex flex-col gap-3" aria-label="유형별 평균 환산월세">
        <h3 className="m-0 text-[17px] font-semibold tracking-[-0.005em]">유형별 평균 환산월세 (만원)</h3>
        <div className="h-[240px] mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={typeData} layout="vertical" margin={{ top: 8, right: 24, bottom: 0, left: 8 }}>
              <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                stroke={CHART_COLORS.axis}
                tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
                tickMargin={6}
              />
              <YAxis
                type="category"
                dataKey="label"
                stroke={CHART_COLORS.axis}
                tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
                width={80}
                tickMargin={6}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 'var(--font-caption-size)',
                }}
                formatter={(value, _n, item) => {
                  const v = typeof value === 'number' ? value : Number(value);
                  const d = item?.payload as (typeof typeData)[number];
                  if (!d.has) return ['데이터 부족', ''] as [string, string];
                  return [`${v}만원 (${d.count}건)`, '평균'] as [string, string];
                }}
              />
              <Bar dataKey="avg" radius={[0, 4, 4, 0]} barSize={18}>
                {typeData.map((d, i) => (
                  <Cell
                    key={i}
                    fill={d.has ? DEAL_TYPE_FILL[d.deal_type] : CHART_COLORS.grid}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="border border-divider rounded-md bg-surface p-6 flex flex-col gap-3" aria-label="보증금 대역 분포">
        <h3 className="m-0 text-[17px] font-semibold tracking-[-0.005em]">보증금 대역 분포</h3>
        <p className="mono-label m-0 text-text-muted">막대 = 거래 건수, 우측 = 평균 월세</p>
        <div className="h-[240px] mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={bandData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="band"
                stroke={CHART_COLORS.axis}
                tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
              />
              <YAxis
                stroke={CHART_COLORS.axis}
                tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
                width={40}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 'var(--font-caption-size)',
                }}
                formatter={(value, _n, item) => {
                  const v = typeof value === 'number' ? value : Number(value);
                  const d = item?.payload as (typeof bandData)[number];
                  return [`${v}건 · 평균 ${d.monthly}만원`, ''] as [string, string];
                }}
              />
              <Bar dataKey="count" fill={CHART_COLORS.bar} radius={[4, 4, 0, 0]} barSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="border border-divider rounded-md bg-surface p-6 flex flex-col gap-3" aria-label="월별 평균 월세 추이">
        <h3 className="m-0 text-[17px] font-semibold tracking-[-0.005em]">월별 평균 월세 추이 (만원)</h3>
        <div className="h-[240px] mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="month"
                stroke={CHART_COLORS.axis}
                tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                tickMargin={6}
              />
              <YAxis
                stroke={CHART_COLORS.axis}
                tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
                width={36}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 'var(--font-caption-size)',
                }}
                formatter={(v) =>
                  v == null
                    ? (['-', ''] as [string, string])
                    : ([`${v}만원`, ''] as [string, string])
                }
              />
              <Legend
                verticalAlign="top"
                height={24}
                iconType="circle"
                iconSize={6}
                wrapperStyle={{ fontSize: 'var(--font-caption-size)' }}
              />
              <Line type="monotone" dataKey="villa" name="연립다세대" stroke={CHART_COLORS.villa} strokeWidth={2} dot={false} connectNulls={false} />
              <Line type="monotone" dataKey="dagagu" name="다가구" stroke={CHART_COLORS.dagagu} strokeWidth={2} dot={false} connectNulls={false} />
              <Line type="monotone" dataKey="danok" name="단독" stroke={CHART_COLORS.danok} strokeWidth={2} dot={false} connectNulls={false} />
              <Line type="monotone" dataKey="officetel" name="오피스텔" stroke={CHART_COLORS.officetel} strokeWidth={2} dot={false} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function formatBand(b: string): string {
  switch (b) {
    case '0':
      return '0~500';
    case '500':
      return '500~1k';
    case '1000':
      return '1~2k';
    case '2000':
      return '2~3k';
    case '3000+':
      return '3k+';
    default:
      return b;
  }
}

interface DealsBlockProps {
  deals: {
    items: Array<{
      date: string;
      type: string;
      deal_type: ExploreDealType;
      area_m2: number;
      deposit: number;
      monthly_rent: number;
      converted_rent: number;
      house_name: string;
      build_year: number | null;
      floor: number | null;
    }>;
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
  sort: ExploreSort;
  onSortChange: (s: ExploreSort) => void;
  onPageChange: (p: number) => void;
}

function DealsBlock({ deals, sort, onSortChange, onPageChange }: DealsBlockProps) {
  return (
    <section className="border border-divider rounded-md bg-surface p-7" aria-label="거래 표">
      <header className="flex justify-between items-center mb-5 flex-wrap gap-3">
        <h2 className="m-0 text-[22px] font-semibold tracking-[-0.01em]">거래 목록 ({deals.total.toLocaleString()}건)</h2>
        <div className="flex gap-3 items-center">
          <label className="flex items-center gap-2">
            <span className="mono-label">정렬</span>
            <select
              value={sort}
              onChange={(e) => onSortChange(e.target.value as ExploreSort)}
              className="py-2 px-3 border border-divider rounded-sm bg-surface text-body-base text-text"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-body-base">
          <thead>
            <tr>
              <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-left uppercase py-4 px-5 border-b border-divider">날짜</th>
              <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-left uppercase py-4 px-5 border-b border-divider">유형</th>
              <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-left uppercase py-4 px-5 border-b border-divider">건물명</th>
              <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-right uppercase py-4 px-5 border-b border-divider">면적</th>
              <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-right uppercase py-4 px-5 border-b border-divider">층</th>
              <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-right uppercase py-4 px-5 border-b border-divider">건축</th>
              <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-right uppercase py-4 px-5 border-b border-divider">보증금</th>
              <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-right uppercase py-4 px-5 border-b border-divider">월세</th>
              <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-right uppercase py-4 px-5 border-b border-divider">환산</th>
            </tr>
          </thead>
          <tbody>
            {deals.items.map((d, i) => (
              <tr key={`${d.date}-${i}`} className="hover:bg-surface-alt">
                <td className="tabular py-4 px-5 border-b border-divider text-text align-middle">{d.date}</td>
                <td className="py-4 px-5 border-b border-divider text-text align-middle">{d.type}</td>
                <td className="py-4 px-5 border-b border-divider text-text align-middle max-w-[200px] whitespace-nowrap overflow-hidden text-ellipsis">{d.house_name || '-'}</td>
                <td className="tabular py-4 px-5 border-b border-divider text-text align-middle text-right">{d.area_m2.toFixed(1)}m²</td>
                <td className="tabular py-4 px-5 border-b border-divider text-text align-middle text-right">{d.floor != null ? `${d.floor}층` : '-'}</td>
                <td className="tabular py-4 px-5 border-b border-divider text-text align-middle text-right">{d.build_year != null ? `'${String(d.build_year).slice(-2)}` : '-'}</td>
                <td className="tabular py-4 px-5 border-b border-divider text-text align-middle text-right">{d.deposit.toLocaleString()}</td>
                <td className="tabular py-4 px-5 border-b border-divider text-text align-middle text-right">{d.monthly_rent === 0 ? '-' : d.monthly_rent}</td>
                <td className="tabular font-semibold py-4 px-5 border-b border-divider text-text align-middle text-right">{d.converted_rent}</td>
              </tr>
            ))}
            {deals.items.length === 0 ? (
              <tr>
                <td colSpan={9} className="text-center text-text-muted p-6">
                  필터에 맞는 거래가 없습니다. 좌측 필터 범위를 넓혀보세요.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {deals.total_pages > 1 ? (
        <PaginationNav
          page={deals.page}
          totalPages={deals.total_pages}
          onChange={onPageChange}
        />
      ) : null}
    </section>
  );
}

function PaginationNav({
  page,
  totalPages,
  onChange,
}: {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
}) {
  const can = (target: number) => target >= 1 && target <= totalPages && target !== page;
  return (
    <div className="flex justify-center items-center gap-4 mt-5" role="navigation">
      <button
        type="button"
        disabled={!can(page - 1)}
        onClick={() => onChange(page - 1)}
        className="py-2 px-4 border border-divider bg-surface rounded-sm text-text cursor-pointer text-body-base disabled:text-text-muted disabled:cursor-not-allowed disabled:bg-surface-alt"
      >
        이전
      </button>
      <span className="tabular text-text-subtle text-body-base">
        {page} / {totalPages}
      </span>
      <button
        type="button"
        disabled={!can(page + 1)}
        onClick={() => onChange(page + 1)}
        className="py-2 px-4 border border-divider bg-surface rounded-sm text-text cursor-pointer text-body-base disabled:text-text-muted disabled:cursor-not-allowed disabled:bg-surface-alt"
      >
        다음
      </button>
    </div>
  );
}
