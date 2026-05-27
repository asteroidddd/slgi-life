// RealEstateSection — SPEC 6.3 Section 2 (자취 시장 대시보드).
//
// Phase 4.7: "최근 5건만" 표 기반 → 자취생 친화 풀 대시보드로 확장.
import { useState } from 'react';
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
import { formatConvertedRent } from '@/lib/rent';
import type { AdongDetail } from '@/types/api';

type DealTypeKey = 'villa' | 'dagagu' | 'danok' | 'officetel';

const DEAL_TYPE_FILL: Record<DealTypeKey, string> = {
  villa: CHART_COLORS.villa,
  dagagu: CHART_COLORS.dagagu,
  danok: CHART_COLORS.danok,
  officetel: CHART_COLORS.officetel,
};

interface RealEstateSectionProps {
  realEstate: AdongDetail['real_estate'];
}

type Period = '3m' | '6m' | '12m';

const PERIOD_OPTIONS: Array<{ value: Period; label: string; months: number }> = [
  { value: '3m', label: '3개월', months: 3 },
  { value: '6m', label: '6개월', months: 6 },
  { value: '12m', label: '12개월', months: 12 },
];

export default function RealEstateSection({ realEstate }: RealEstateSectionProps) {
  const [period, setPeriod] = useState<Period>('6m');

  const months = PERIOD_OPTIONS.find((p) => p.value === period)?.months ?? 6;
  const trend = realEstate.monthly_trend.slice(-months);

  const bands = realEstate.deposit_band_avg.map((b) => ({
    band: formatBandLabel(b.band),
    monthly: b.avg_monthly_rent,
  }));

  const kpi = realEstate.studio_kpi;
  const typeAvg = realEstate.type_avg.map((t) => ({
    label: t.label,
    avg: t.avg_converted_rent ?? 0,
    has: t.avg_converted_rent !== null,
    deal_type: t.deal_type,
    count: t.count,
  }));

  const scatterByType: Record<DealTypeKey, Array<{ x: number; y: number }>> = {
    villa: [],
    dagagu: [],
    danok: [],
    officetel: [],
  };
  for (const p of realEstate.scatter) {
    scatterByType[p.deal_type as DealTypeKey]?.push({
      x: p.area_m2,
      y: p.converted_rent,
    });
  }

  return (
    <section
      className="max-w-[720px] pt-20 border-t border-divider"
      aria-labelledby="rent-heading"
    >
      <p className="mono-label m-0 mb-3 text-text-subtle" aria-hidden="true">
        STUDIO MARKET / 자취 시세
      </p>
      <header className="flex items-center justify-between gap-4 mb-6">
        <h2 id="rent-heading" className="m-0 text-section-heading leading-[1.15] font-semibold text-text tracking-[-0.36px]">
          자취 시세 대시보드
        </h2>
        <div
          className="inline-flex gap-1 bg-surface-alt border border-border rounded-xl p-1"
          role="tablist"
          aria-label="기간 선택"
        >
          {PERIOD_OPTIONS.map((opt) => {
            const active = opt.value === period;
            return (
              <button
                key={opt.value}
                type="button"
                role="tab"
                aria-selected={active}
                className={`appearance-none border-none cursor-pointer h-[var(--control-height-sm)] px-3 text-caption tracking-normal rounded-pill transition-all duration-[120ms] ease-out ${
                  active
                    ? 'bg-secondary text-surface font-medium'
                    : 'bg-transparent text-text-muted hover:text-text'
                } focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-1`}
                onClick={() => setPeriod(opt.value)}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </header>

      <p className="mono-label my-1 mb-5 text-text-muted">
        아파트 제외 · 보증금 5억 이하 · 최근 6개월 자취 시장 기준
      </p>

      <div className="grid grid-cols-4 gap-4 mb-[var(--space-7)]" aria-label="자취 시장 핵심 지표">
        <KpiCard
          label="평균 환산월세"
          value={kpi.avg_converted_rent != null ? `${kpi.avg_converted_rent}만원` : '-'}
          hint="월세 + 보증금 × 0.005"
        />
        <KpiCard
          label="최저 보증금"
          value={kpi.min_deposit != null ? `${kpi.min_deposit.toLocaleString()}만원` : '-'}
          hint="자취 시장 진입 가격"
        />
        <KpiCard
          label="평균 면적"
          value={kpi.avg_area_m2 != null ? `${kpi.avg_area_m2}m²` : '-'}
          hint={kpi.avg_area_m2 != null ? `약 ${(kpi.avg_area_m2 / 3.3058).toFixed(1)}평` : ''}
        />
        <KpiCard
          label="최근 6개월 거래"
          value={kpi.recent_count.toLocaleString()}
          hint="아파트 제외, 자취 가능 매물"
        />
      </div>

      <div className="grid grid-cols-2 gap-6 mb-8">
        <div className="flex flex-col gap-2" aria-label="유형별 평균 환산월세">
          <h3 className="m-0 text-feature-heading leading-[1.3] font-semibold text-text">유형별 평균 환산월세 (만원)</h3>
          <p className="mono-label m-0 text-text-subtle">
            거래 3건 미만 유형은 회색 처리
          </p>
          <div className="w-full h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={typeAvg}
                layout="vertical"
                margin={{ top: 8, right: 24, bottom: 0, left: 8 }}
              >
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
                  labelStyle={{ color: 'var(--color-text)' }}
                  formatter={(value, _n, item) => {
                    const v = typeof value === 'number' ? value : Number(value);
                    const datum = item?.payload as (typeof typeAvg)[number];
                    if (!datum.has) return ['데이터 부족', ''] as [string, string];
                    return [`${v}만원 (${datum.count}건)`, '평균 환산월세'] as [
                      string,
                      string,
                    ];
                  }}
                />
                <Bar dataKey="avg" radius={[0, 4, 4, 0]} barSize={18}>
                  {typeAvg.map((d, i) => (
                    <Cell
                      key={i}
                      fill={
                        d.has
                          ? DEAL_TYPE_FILL[d.deal_type as DealTypeKey]
                          : CHART_COLORS.grid
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="flex flex-col gap-2" aria-label="면적-환산월세 산점도">
          <h3 className="m-0 text-feature-heading leading-[1.3] font-semibold text-text">면적·환산월세 분포</h3>
          <p className="mono-label m-0 text-text-subtle">
            최근 6개월, 점 하나 = 거래 1건 (최대 200건)
          </p>
          <div className="w-full h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="면적"
                  unit="m²"
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
                  tickMargin={6}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="환산월세"
                  unit="만원"
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
                  tickMargin={6}
                  width={48}
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
                  labelStyle={{ color: 'var(--color-text)' }}
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
                <Scatter
                  name="연립다세대"
                  data={scatterByType.villa}
                  fill={CHART_COLORS.villa}
                  fillOpacity={0.7}
                />
                <Scatter
                  name="다가구"
                  data={scatterByType.dagagu}
                  fill={CHART_COLORS.dagagu}
                  fillOpacity={0.7}
                />
                <Scatter
                  name="단독"
                  data={scatterByType.danok}
                  fill={CHART_COLORS.danok}
                  fillOpacity={0.7}
                />
                <Scatter
                  name="오피스텔"
                  data={scatterByType.officetel}
                  fill={CHART_COLORS.officetel}
                  fillOpacity={0.7}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="flex flex-col gap-2" aria-label="월별 평균 월세 추이">
          <h3 className="m-0 text-feature-heading leading-[1.3] font-semibold text-text">월별 평균 월세 (raw, 만원)</h3>
          <p className="mono-label m-0 text-text-subtle">
            보증금 환산 전 — 환산값은 아래 거래표 참고
          </p>
          <div className="w-full h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="month"
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
                  tickMargin={6}
                />
                <YAxis
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
                  tickMargin={6}
                  width={40}
                />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: 'var(--font-caption-size)',
                  }}
                  labelStyle={{ color: 'var(--color-text)' }}
                  formatter={(value) => {
                    const v = value as number | null | undefined;
                    return v == null
                      ? (['-', ''] as [string, string])
                      : ([`${v}만원`, ''] as [string, string]);
                  }}
                />
                <Legend
                  verticalAlign="top"
                  height={28}
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: 'var(--font-caption-size)' }}
                />
                <Line type="monotone" dataKey="villa" name="연립다세대" stroke={CHART_COLORS.villa} strokeWidth={2} connectNulls={false} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                <Line type="monotone" dataKey="dagagu" name="다가구" stroke={CHART_COLORS.dagagu} strokeWidth={2} connectNulls={false} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                <Line type="monotone" dataKey="danok" name="단독" stroke={CHART_COLORS.danok} strokeWidth={2} connectNulls={false} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                <Line type="monotone" dataKey="officetel" name="오피스텔" stroke={CHART_COLORS.officetel} strokeWidth={2} connectNulls={false} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="flex flex-col gap-2" aria-label="보증금 구간별 평균 월세">
          <h3 className="m-0 text-feature-heading leading-[1.3] font-semibold text-text">보증금 구간별 평균 월세 (만원)</h3>
          <div className="w-full h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={bands}
                layout="vertical"
                margin={{ top: 8, right: 24, bottom: 0, left: 8 }}
              >
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 11 }}
                  tickMargin={6}
                />
                <YAxis
                  type="category"
                  dataKey="band"
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
                  labelStyle={{ color: 'var(--color-text)' }}
                  formatter={(value) => {
                    const v = value as number;
                    return [`${v}만원`, '평균 월세'] as [string, string];
                  }}
                />
                <Bar
                  dataKey="monthly"
                  fill={CHART_COLORS.villa}
                  radius={[0, 4, 4, 0]}
                  barSize={18}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3" aria-label="최근 자취 거래 5건">
        <header className="flex flex-wrap items-baseline justify-between gap-3 pb-2 border-b border-divider">
          <h3 className="m-0 text-feature-heading leading-[1.3] font-semibold text-text">최근 자취 거래 5건</h3>
          <p className="mono-label m-0 text-text-subtle">
            아파트 제외 · 환산 = 월세 + 보증금 × 0.005 (연 6%)
          </p>
        </header>
        <div className="w-full overflow-x-auto">
          <table className="w-full border-collapse text-body-base">
            <thead>
              <tr>
                <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-left uppercase py-3 px-5 border-b border-divider">날짜</th>
                <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-left uppercase py-3 px-5 border-b border-divider">유형</th>
                <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-left uppercase py-3 px-5 border-b border-divider">면적</th>
                <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-left uppercase py-3 px-5 border-b border-divider">보증금</th>
                <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-left uppercase py-3 px-5 border-b border-divider">월세</th>
                <th scope="col" className="bg-surface-alt text-text-subtle font-mono text-mono-label font-normal tracking-[0.26px] text-left uppercase py-3 px-5 border-b border-divider">환산 월세</th>
              </tr>
            </thead>
            <tbody>
              {realEstate.recent_deals.map((deal, idx) => (
                <tr key={`${deal.date}-${idx}`}>
                  <td className="tabular py-3 px-5 border-b border-divider text-text tracking-normal last:[&]:border-b-0">{deal.date}</td>
                  <td className="py-3 px-5 border-b border-divider text-text tracking-normal">{deal.type}</td>
                  <td className="tabular py-3 px-5 border-b border-divider text-text tracking-normal">{deal.area_m2.toFixed(1)}m²</td>
                  <td className="tabular py-3 px-5 border-b border-divider text-text tracking-normal">{deal.deposit.toLocaleString()}만원</td>
                  <td className="tabular py-3 px-5 border-b border-divider text-text tracking-normal">
                    {deal.monthly_rent === 0 ? '-' : `${deal.monthly_rent}만원`}
                  </td>
                  <td className="tabular py-3 px-5 border-b border-divider text-text tracking-normal font-mono">
                    {formatConvertedRent(deal.deposit, deal.monthly_rent)}
                    {deal.monthly_rent === 0 && (
                      <span className="mono-label text-text-subtle ml-1"> 전세</span>
                    )}
                  </td>
                </tr>
              ))}
              {realEstate.recent_deals.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center text-text-muted p-6">
                    최근 실거래 내역이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function formatBandLabel(band: string): string {
  switch (band) {
    case '0':
      return '0~500';
    case '500':
      return '500~1000';
    case '1000':
      return '1000~2000';
    case '2000':
      return '2000~3000';
    case '3000+':
      return '3000+';
    default:
      return band;
  }
}

interface KpiCardProps {
  label: string;
  value: string;
  hint?: string;
}

function KpiCard({ label, value, hint }: KpiCardProps) {
  return (
    <div className="p-5 border border-divider rounded-md bg-surface flex flex-col gap-2">
      <p className="mono-label m-0 text-text-subtle">{label}</p>
      <p className="tabular m-0 text-[28px] font-semibold text-text leading-[1.1]">{value}</p>
      {hint ? <p className="m-0 text-caption text-text-muted">{hint}</p> : null}
    </div>
  );
}
