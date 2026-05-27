// Dashboard SafetyEconomySection -- SPEC 4.4 Section E (안전·환경·경제).
//
// All data is gu-level (○○구 단위 뱃지). Metric codes from gu_metric table:
//   Safety:        SAFETY_GRADE_TRAFFIC, _CRIME, _FIRE, _DISEASE, _LIFE, _SUICIDE
//   Accidents:     ACC_TOTAL_COUNT, ACC_INJURY_COUNT, ACC_DRUNK_COUNT, ACC_HITRUN_COUNT
//   Green/Urban:   AREA_GREEN, AREA_URBAN
//   Economy:       GRDP_CURRENT, POP_RESIDENT (for per-capita)
//   Fire:          FIRE_COUNT
//   Transit (B3):  TRAFFIC_CULTURE_INDEX, TRAFFIC_SAFETY, TRAFFIC_WALK,
//                  TRAFFIC_DRIVE, TRAFFIC_VULNERABLE
//
// Data: AdongGuMetricsResponse

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import { CATEGORY_COLORS, CHART_COLORS } from '@/lib/colors';
import type {
  AdongGuMetricsResponse,
  GuMetricSeriesPoint,
  GuMetricSeriesResponse,
} from '@/types/api';

interface SafetyEconomySectionProps {
  guMetrics: AdongGuMetricsResponse;
  /** Optional time-series payload (ACC_TOTAL_COUNT / FIRE_COUNT) for the
   *  trend line charts. May be undefined while loading; charts render an
   *  empty state when the corresponding code has zero points. */
  series?: GuMetricSeriesResponse;
}

/** One row in the combined trend chart dataset (gu + 25구 평균). */
interface SeriesRow {
  date: string;
  gu: number | null;
  guAvg: number | null;
}

/** Combine gu points + 25구 평균 points into a single dataset keyed by date.
 *  Both source arrays are date-ASC (backend invariant), but use null-fills
 *  rather than assuming exact date alignment. */
function mergeSeries(
  guPoints: GuMetricSeriesPoint[] | undefined,
  guAvgPoints: GuMetricSeriesPoint[] | undefined,
): SeriesRow[] {
  const guMap = new Map<string, number | null>();
  (guPoints ?? []).forEach((p) => guMap.set(p.date, p.value));
  const avgMap = new Map<string, number | null>();
  (guAvgPoints ?? []).forEach((p) => avgMap.set(p.date, p.value));
  const dates = Array.from(new Set([...guMap.keys(), ...avgMap.keys()])).sort();
  return dates.map((date) => ({
    date,
    gu: guMap.get(date) ?? null,
    guAvg: avgMap.get(date) ?? null,
  }));
}

/** 'YYYY-MM-DD' → 'YYYY' (annual data ticks). */
function formatYearTick(date: string): string {
  return date.slice(0, 4);
}

function paddedDomain(rows: SeriesRow[]): [number, number] {
  const values = rows.flatMap((r) => [r.gu, r.guAvg]).filter((v): v is number => v != null);
  if (values.length === 0) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(1, max - min);
  const pad = range * 0.15;
  return [Math.max(0, Math.floor(min - pad)), Math.ceil(max + pad)];
}

const TOOLTIP_STYLE = {
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  fontSize: 'var(--font-caption-size)',
};

/** Format ISO date "YYYY-MM-DD" → "YYYY년 기준". null/undefined → empty. */
function formatMetricDate(date: string | null | undefined): string {
  if (!date) return '';
  return `${date.slice(0, 4)}년 기준`;
}

/** Helper to get metric value with fallback. */
function mv(
  metrics: AdongGuMetricsResponse['metrics'],
  code: string,
): number | null {
  return metrics[code]?.value ?? null;
}

/** Helper to get metric date. */
function mDate(
  metrics: AdongGuMetricsResponse['metrics'],
  code: string,
): string | null | undefined {
  return metrics[code]?.date;
}

/** Helper to get 25-구 average value for a code. */
function ga(
  metrics: AdongGuMetricsResponse['metrics'],
  code: string,
): number | null {
  return metrics[code]?.gu_avg ?? null;
}

/** Helper to get rank in Seoul (25구 중 N위). */
function rank(
  metrics: AdongGuMetricsResponse['metrics'],
  code: string,
): number | null {
  return metrics[code]?.rank_in_seoul ?? null;
}

function formatNumber(n: number): string {
  if (Number.isInteger(n)) return n.toLocaleString();
  if (Math.abs(n) >= 1000) return Math.round(n).toLocaleString();
  return n.toFixed(1);
}

/** Render a metric card with value, 25-구 평균 비교, unit, optional date footer.
 *  rank: 25구 중 순위 (작을수록 값이 큼). 표기는 "N위 / 25구". */
function MetricCard({
  label,
  value,
  guAvg,
  unit,
  date,
  rank,
  higherIsBetter = true,
  formatter,
  insight,
}: {
  label: string;
  value: number | null;
  guAvg: number | null;
  unit: string;
  date?: string | null;
  rank?: number | null;
  higherIsBetter?: boolean;
  formatter?: (n: number) => string;
  insight?: string | null;
}) {
  const fmt = formatter ?? formatNumber;
  const diff = value != null && guAvg != null ? value - guAvg : null;
  const isGood = diff != null ? (higherIsBetter ? diff >= 0 : diff <= 0) : null;
  const dateText = formatMetricDate(date);

  return (
    <div className="p-2 rounded-card border border-divider bg-surface">
      <p className="text-[12px] m-0 mb-1 text-text-subtle">{label}</p>
      <p className="tabular m-0 text-[18px] font-semibold text-text leading-[1.1]">
        {value != null ? `${fmt(value)}${unit}` : '-'}
      </p>
      {guAvg != null && diff != null && (
        <p className="m-0 mt-1 text-[12px] text-text-muted">
          25구 평균 {fmt(guAvg)}{unit}
          <span className={`ml-1 font-medium ${isGood ? 'text-success' : 'text-danger'}`}>
            {diff >= 0 ? '▲' : '▼'}
            {fmt(Math.abs(diff))}{unit}
          </span>
        </p>
      )}
      {rank != null && (
        <p className="m-0 mt-1 text-[12px] text-text-subtle">25구 중 {rank}위</p>
      )}
      {insight && (
        <span className="inline-flex items-center mt-1 px-2.5 py-1 rounded-full bg-primary-soft text-[13px] font-semibold text-primary">{insight}</span>
      )}
      {dateText && (
        <p className="m-0 mt-1 text-[11px] text-text-subtle">{dateText}</p>
      )}
    </div>
  );
}

// Safety radar field definitions — 6 SAFETY_GRADE sub-fields (실제 응답 코드 기준)
const SAFETY_FIELDS = [
  { code: 'SAFETY_GRADE_TRAFFIC', label: '교통안전' },
  { code: 'SAFETY_GRADE_CRIME', label: '범죄' },
  { code: 'SAFETY_GRADE_FIRE', label: '화재' },
  { code: 'SAFETY_GRADE_DISEASE', label: '생활질병' },
  { code: 'SAFETY_GRADE_LIFE', label: '생활안전' },
  { code: 'SAFETY_GRADE_SUICIDE', label: '자살' },
] as const;

// Transit culture radar (B3) — 4 sub-fields under TRAFFIC_CULTURE_INDEX
const TRAFFIC_CULTURE_FIELDS = [
  { code: 'TRAFFIC_SAFETY', label: '안전' },
  { code: 'TRAFFIC_WALK', label: '보행' },
  { code: 'TRAFFIC_DRIVE', label: '운전' },
  { code: 'TRAFFIC_VULNERABLE', label: '교통약자' },
] as const;

export default function SafetyEconomySection({
  guMetrics,
  series,
}: SafetyEconomySectionProps) {
  const { metrics, gu_name } = guMetrics;

  // Phase 4: 추이 차트 데이터 (교통사고 / 화재). 비교선은 25구 평균.
  const accSeries = series?.series['ACC_TOTAL_COUNT'];
  const fireSeries = series?.series['FIRE_COUNT'];
  const accGuAvgSeries = series?.gu_avg_series?.['ACC_TOTAL_COUNT'];
  const fireGuAvgSeries = series?.gu_avg_series?.['FIRE_COUNT'];
  const accTrendData = mergeSeries(accSeries?.points, accGuAvgSeries?.points);
  const fireTrendData = mergeSeries(fireSeries?.points, fireGuAvgSeries?.points);
  const hasAccTrend = (accSeries?.points.length ?? 0) > 0;
  const hasFireTrend = (fireSeries?.points.length ?? 0) > 0;
  const accYAxisDomain = paddedDomain(accTrendData);
  const fireYAxisDomain = paddedDomain(fireTrendData);
  const accRank = accSeries?.current_rank ?? null;
  const fireRank = fireSeries?.current_rank ?? null;

  // 1. Safety radar data — 1~5 scale, higher is safer. 비교선은 25구 평균.
  const radarData = SAFETY_FIELDS.map((f) => ({
    subject: f.label,
    구: mv(metrics, f.code),
    평균: ga(metrics, f.code),
  }));
  const hasRadarData = radarData.some((d) => d.구 != null);

  // Composite safety grade — mean of 6 sub-fields (since SAFETY_GRADE_MEAN not in response)
  const safetyValues = SAFETY_FIELDS.map((f) => mv(metrics, f.code)).filter(
    (v): v is number => v != null,
  );
  const safetyMean =
    safetyValues.length > 0
      ? safetyValues.reduce((a, b) => a + b, 0) / safetyValues.length
      : null;
  const guAvgSafetyValues = SAFETY_FIELDS.map((f) => ga(metrics, f.code)).filter(
    (v): v is number => v != null,
  );
  const guAvgSafetyMean =
    guAvgSafetyValues.length > 0
      ? guAvgSafetyValues.reduce((a, b) => a + b, 0) / guAvgSafetyValues.length
      : null;
  const safetyDate = formatMetricDate(mDate(metrics, 'SAFETY_GRADE_TRAFFIC'));

  // Safety insight text
  const safetyInsight =
    safetyMean != null && guAvgSafetyMean != null
      ? safetyMean > guAvgSafetyMean
        ? '서울 평균보다 안전한 구예요'
        : '안전 지표가 서울 평균보다 낮아요'
      : null;

  // Shared population values (used by accident per-capita AND green/GRDP sections)
  const popResident = mv(metrics, 'POP_RESIDENT');
  const guAvgPopResident = ga(metrics, 'POP_RESIDENT');

  // 2. Accident metrics — 실제 코드 기반
  const accTotal = mv(metrics, 'ACC_TOTAL_COUNT');
  const accInjury = mv(metrics, 'ACC_INJURY_COUNT');
  const accDrunk = mv(metrics, 'ACC_DRUNK_COUNT');
  const accHitrun = mv(metrics, 'ACC_HITRUN_COUNT');
  const guAvgAccTotal = ga(metrics, 'ACC_TOTAL_COUNT');
  const guAvgAccInjury = ga(metrics, 'ACC_INJURY_COUNT');
  const accTotalRank = rank(metrics, 'ACC_TOTAL_COUNT');

  // 인구 10만명당 사고율 (구 비교용)
  const accPer100k =
    accTotal != null && popResident != null && popResident > 0
      ? (accTotal / popResident) * 100_000
      : null;
  const guAvgAccPer100k =
    guAvgAccTotal != null && guAvgPopResident != null && guAvgPopResident > 0
      ? (guAvgAccTotal / guAvgPopResident) * 100_000
      : null;

  // Accident insight text
  const accidentInsight =
    accPer100k != null && guAvgAccPer100k != null
      ? accPer100k < guAvgAccPer100k
        ? '사고율이 낮아 안심할 수 있어요'
        : '사고율이 서울 평균보다 높은 편이에요'
      : null;

  // 음주/뺑소니는 절대값 → 총건수 대비 비율로 변환
  const accDrunkRatio =
    accDrunk != null && accTotal != null && accTotal > 0 ? (accDrunk / accTotal) * 100 : null;
  const accHitrunRatio =
    accHitrun != null && accTotal != null && accTotal > 0 ? (accHitrun / accTotal) * 100 : null;
  const accDate = formatMetricDate(mDate(metrics, 'ACC_TOTAL_COUNT'));

  const accBarData = [
    ...(accDrunkRatio != null ? [{ name: '음주사고 비율', value: accDrunkRatio }] : []),
    ...(accHitrunRatio != null ? [{ name: '뺑소니 비율', value: accHitrunRatio }] : []),
  ];
  const accBarColors = [CHART_COLORS.warningDeep, CATEGORY_COLORS.safety];

  // 3. Green area metrics — AREA_GREEN, AREA_URBAN (25구 평균 비교)
  const areaGreen = mv(metrics, 'AREA_GREEN');
  const areaUrban = mv(metrics, 'AREA_URBAN');
  const guAvgAreaGreen = ga(metrics, 'AREA_GREEN');
  const guAvgAreaUrban = ga(metrics, 'AREA_URBAN');

  const greenRatio =
    areaGreen != null && areaUrban != null && areaGreen + areaUrban > 0
      ? (areaGreen / (areaGreen + areaUrban)) * 100
      : null;
  const guAvgGreenRatio =
    guAvgAreaGreen != null && guAvgAreaUrban != null && guAvgAreaGreen + guAvgAreaUrban > 0
      ? (guAvgAreaGreen / (guAvgAreaGreen + guAvgAreaUrban)) * 100
      : null;

  // Green insight text
  const greenInsight =
    greenRatio != null && guAvgGreenRatio != null
      ? greenRatio > guAvgGreenRatio
        ? '녹지가 풍부한 구예요'
        : '녹지 비율이 서울 평균보다 낮아요'
      : null;

  // 4. GRDP — GRDP_CURRENT (백만원 단위) ÷ POP_RESIDENT (25구 평균 비교)
  const grdpCurrent = mv(metrics, 'GRDP_CURRENT');
  const guAvgGrdpCurrent = ga(metrics, 'GRDP_CURRENT');
  const grdpPerCapita =
    grdpCurrent != null && popResident != null && popResident > 0
      ? grdpCurrent / popResident
      : null;
  const guAvgGrdpPerCapita =
    guAvgGrdpCurrent != null && guAvgPopResident != null && guAvgPopResident > 0
      ? guAvgGrdpCurrent / guAvgPopResident
      : null;
  const grdpDate = formatMetricDate(mDate(metrics, 'GRDP_CURRENT'));
  const grdpRank = rank(metrics, 'GRDP_CURRENT');

  // GRDP 총액 — 백만원 → 조원 (÷ 1,000,000)
  const grdpTotalJo = grdpCurrent != null ? grdpCurrent / 1_000_000 : null;

  // GRDP insight text
  const grdpInsight =
    grdpPerCapita != null && guAvgGrdpPerCapita != null
      ? grdpPerCapita > guAvgGrdpPerCapita
        ? '경제 활동이 활발한 구예요'
        : '1인당 경제규모가 서울 평균보다 작은 편이에요'
      : null;

  // 5. Fire count (25구 평균 비교)
  const fireCount = mv(metrics, 'FIRE_COUNT');
  const guAvgFireCount = ga(metrics, 'FIRE_COUNT');

  // B3. Traffic culture radar (25구 평균 비교)
  const trafficCultureIndex = mv(metrics, 'TRAFFIC_CULTURE_INDEX');
  const guAvgTrafficCultureIndex = ga(metrics, 'TRAFFIC_CULTURE_INDEX');
  const trafficCultureRank = rank(metrics, 'TRAFFIC_CULTURE_INDEX');
  const trafficRadarData = TRAFFIC_CULTURE_FIELDS.map((f) => ({
    subject: f.label,
    구: mv(metrics, f.code),
    평균: ga(metrics, f.code),
  }));
  const hasTrafficRadar = trafficRadarData.some((d) => d.구 != null);
  const trafficCultureDate = formatMetricDate(mDate(metrics, 'TRAFFIC_CULTURE_INDEX'));

  return (
    <div className="flex flex-col gap-2">
      {/* Badge: all data is gu-level */}
      <div className="flex items-center gap-2">
        <Badge variant="neutral" size="sm">
          {gu_name} 단위
        </Badge>
        <span className="text-[12px] text-text-muted">
          모든 지표는 자치구 단위 데이터입니다
        </span>
      </div>

      {/* Row 1: Safety radar (with composite text) + Accident stats */}
      <div className="grid grid-cols-2 gap-2">
        {/* 1. Safety radar */}
        <Card padding="md">
          <div className="flex items-baseline justify-between mb-1">
            <h3 className="m-0 text-[16px] leading-snug font-semibold text-text">
              안전 등급 (6분야)
            </h3>
            {safetyMean != null && (
              <p className="m-0 tabular text-[12px] text-text-muted">
                종합{' '}
                <span className="text-[13px] font-semibold text-text">
                  {safetyMean.toFixed(1)}
                </span>
                {guAvgSafetyMean != null && (
                  <span className="ml-1">/ 25구 평균 {guAvgSafetyMean.toFixed(1)}</span>
                )}
              </p>
            )}
          </div>
          {hasRadarData ? (
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke={CHART_COLORS.grid} />
                  <PolarAngleAxis
                    dataKey="subject"
                    tick={{ fontSize: 11, fill: CHART_COLORS.axis }}
                  />
                  <PolarRadiusAxis
                    angle={90}
                    domain={[0, 5]}
                    tick={{ fontSize: 9, fill: CHART_COLORS.axis }}
                    tickCount={6}
                  />
                  <Radar
                    name={gu_name}
                    dataKey="구"
                    stroke={CATEGORY_COLORS.safety}
                    fill={CATEGORY_COLORS.safety}
                    fillOpacity={0.25}
                    isAnimationActive={true}
                    animationDuration={1200}
                  />
                  <Radar
                    name="25구 평균"
                    dataKey="평균"
                    stroke={CHART_COLORS.axis}
                    fill={CHART_COLORS.axis}
                    fillOpacity={0.08}
                    strokeDasharray="4 4"
                    isAnimationActive={true}
                    animationDuration={1200}
                    animationBegin={300}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[280px] text-text-muted text-[12px]">
              안전 등급 데이터가 없습니다
            </div>
          )}
          {safetyInsight && (
            <span className="inline-flex items-center mt-1 px-2.5 py-1 rounded-full bg-primary-soft text-[13px] font-semibold text-primary">{safetyInsight}</span>
          )}
          <p className="m-0 mt-1 text-[11px] text-text-subtle">
            행정안전부 지역안전등급 · 1~5점(높을수록 안전) · {safetyDate || '연간'}
          </p>
        </Card>

        {/* 2. Accident stats */}
        <Card padding="md">
          <div className="flex items-baseline justify-between mb-1">
            <h3 className="m-0 text-[16px] leading-snug font-semibold text-text">
              교통사고
            </h3>
            {accTotalRank != null && (
              <Badge variant="neutral" size="sm">
                {accTotalRank}위 / 25구
              </Badge>
            )}
          </div>
          {/* 인구 10만명당 사고율 — 구 간 비교 가능한 지표 */}
          {accPer100k != null && (
            <div className="p-2 rounded-card border border-divider bg-surface mb-1">
              <p className="text-[12px] m-0 mb-1 text-text-subtle">인구 10만명당 사고</p>
              <p className="tabular m-0 text-[18px] font-semibold text-text leading-[1.1]">
                {accPer100k.toFixed(0)}
                <span className="ml-1 text-[13px] font-medium text-text-muted">건</span>
              </p>
              {guAvgAccPer100k != null && (
                <p className="m-0 mt-1 text-[12px] text-text-muted">
                  25구 평균 {guAvgAccPer100k.toFixed(0)}건
                  <span className={`ml-1 font-medium ${accPer100k <= guAvgAccPer100k ? 'text-success' : 'text-danger'}`}>
                    {accPer100k >= guAvgAccPer100k ? '▲' : '▼'}
                    {Math.abs(accPer100k - guAvgAccPer100k).toFixed(0)}건
                  </span>
                </p>
              )}
            </div>
          )}
          {accidentInsight && (
            <span className="inline-flex items-center mb-1 px-2.5 py-1 rounded-full bg-primary-soft text-[13px] font-semibold text-primary">{accidentInsight}</span>
          )}
          <div className="grid grid-cols-2 gap-2 mb-2">
            <div className="p-2 rounded-card border border-divider bg-surface">
              <p className="text-[12px] m-0 mb-1 text-text-subtle">총 발생건수</p>
              <p className="tabular m-0 text-[15px] leading-snug font-semibold text-text">
                {accTotal != null ? `${accTotal.toLocaleString()}건` : '-'}
              </p>
              {guAvgAccTotal != null && accTotal != null && (
                <p className="m-0 mt-1 text-[12px] text-text-muted">
                  25구 평균 {Math.round(guAvgAccTotal).toLocaleString()}건
                </p>
              )}
            </div>
            <div className="p-2 rounded-card border border-divider bg-surface">
              <p className="text-[12px] m-0 mb-1 text-text-subtle">부상자수</p>
              <p className="tabular m-0 text-[15px] leading-snug font-semibold text-danger">
                {accInjury != null ? `${accInjury.toLocaleString()}명` : '-'}
              </p>
              {guAvgAccInjury != null && accInjury != null && (
                <p className="m-0 mt-1 text-[12px] text-text-muted">
                  25구 평균 {Math.round(guAvgAccInjury).toLocaleString()}명
                </p>
              )}
            </div>
          </div>
          {accBarData.length > 0 ? (
            <div className="h-[80px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={accBarData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 10, fill: CHART_COLORS.axis }}
                    tickFormatter={(v: number) => `${v.toFixed(1)}%`}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 11, fill: CHART_COLORS.axis }}
                    width={100}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    formatter={(value) => {
                      const v = value as number;
                      return [`${v.toFixed(1)}%`, ''];
                    }}
                  />
                  <Bar
                    dataKey="value"
                    radius={[0, 4, 4, 0]}
                    isAnimationActive={true}
                    animationDuration={800}
                  >
                    {accBarData.map((_, idx) => (
                      <Cell key={idx} fill={accBarColors[idx]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[80px] text-text-muted text-[12px]">
              음주/뺑소니 비율 데이터가 없습니다
            </div>
          )}
          {accDate && (
            <p className="m-0 mt-1 text-[11px] text-text-subtle">{accDate}</p>
          )}
        </Card>
      </div>

      {/* Row 1.5 (Phase 4): 교통사고 추이 + 화재 추이 라인 차트 */}
      <div className="grid grid-cols-2 gap-2">
        {/* 교통사고 추이 라인 */}
        <Card padding="md">
          <div className="flex items-baseline justify-between mb-1">
            <h3 className="m-0 text-[16px] leading-snug font-semibold text-text">
              교통사고 추이
            </h3>
            {accRank && (
              <Badge variant="neutral" size="sm">
                {accRank.rank}위 / {accRank.total}구
              </Badge>
            )}
          </div>
          {hasAccTrend ? (
            <div className="h-[140px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={accTrendData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: CHART_COLORS.axis }}
                    tickFormatter={formatYearTick}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: CHART_COLORS.axis }}
                    tickFormatter={(v: number) => v.toLocaleString()}
                    domain={accYAxisDomain}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    labelFormatter={(label) => formatYearTick(String(label))}
                    formatter={(value, name) => {
                      if (value == null) return ['-', name];
                      const v = value as number;
                      return [`${v.toLocaleString()}건`, name];
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line
                    name={gu_name}
                    type="monotone"
                    dataKey="gu"
                    stroke={CATEGORY_COLORS.safety}
                    strokeWidth={2}
                    dot={{ r: 3, fill: CATEGORY_COLORS.safety }}
                    activeDot={{ r: 5 }}
                    connectNulls
                    isAnimationActive
                    animationDuration={1200}
                  />
                  <Line
                    name="25구 평균"
                    type="monotone"
                    dataKey="guAvg"
                    stroke={CHART_COLORS.axis}
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                    connectNulls
                    isAnimationActive
                    animationDuration={1200}
                    animationBegin={300}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[140px] text-text-muted text-[12px]">
              교통사고 추이 데이터가 없습니다
            </div>
          )}
          <p className="m-0 mt-1 text-[11px] text-text-subtle">
            도로교통공단 TAAS · 연간 · {accSeries?.unit ?? '건'}
          </p>
        </Card>

        {/* 화재 추이 라인 */}
        <Card padding="md">
          <div className="flex items-baseline justify-between mb-1">
            <h3 className="m-0 text-[16px] leading-snug font-semibold text-text">
              화재 발생 추이
            </h3>
            {fireRank && (
              <Badge variant="neutral" size="sm">
                {fireRank.rank}위 / {fireRank.total}구
              </Badge>
            )}
          </div>
          {hasFireTrend ? (
            <div className="h-[140px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={fireTrendData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: CHART_COLORS.axis }}
                    tickFormatter={formatYearTick}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: CHART_COLORS.axis }}
                    tickFormatter={(v: number) => v.toLocaleString()}
                    domain={fireYAxisDomain}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    labelFormatter={(label) => formatYearTick(String(label))}
                    formatter={(value, name) => {
                      if (value == null) return ['-', name];
                      const v = value as number;
                      return [`${v.toLocaleString()}건`, name];
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line
                    name={gu_name}
                    type="monotone"
                    dataKey="gu"
                    stroke={CHART_COLORS.warningDeep}
                    strokeWidth={2}
                    dot={{ r: 3, fill: CHART_COLORS.warningDeep }}
                    activeDot={{ r: 5 }}
                    connectNulls
                    isAnimationActive
                    animationDuration={1200}
                  />
                  <Line
                    name="25구 평균"
                    type="monotone"
                    dataKey="guAvg"
                    stroke={CHART_COLORS.axis}
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                    connectNulls
                    isAnimationActive
                    animationDuration={1200}
                    animationBegin={300}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[140px] text-text-muted text-[12px]">
              화재 추이 데이터가 없습니다
            </div>
          )}
          <p className="m-0 mt-1 text-[11px] text-text-subtle">
            소방청 화재통계 · 연간 · {fireSeries?.unit ?? '건'}
          </p>
        </Card>
      </div>

      {/* Row 2: Traffic culture radar (B3) + GRDP총액 + GRDP 1인당 */}
      <div className="grid grid-cols-3 gap-2">
        {/* B3. Traffic culture radar */}
        <Card padding="md">
          <div className="flex items-baseline justify-between mb-1">
            <h3 className="m-0 text-[16px] leading-snug font-semibold text-text">
              교통문화지수
            </h3>
            {trafficCultureRank != null && (
              <Badge variant="neutral" size="sm">
                {trafficCultureRank}위 / 25구
              </Badge>
            )}
          </div>
          {trafficCultureIndex != null && (
            <p className="m-0 mb-1 tabular text-[12px] text-text-muted">
              종합{' '}
              <span className="text-[13px] font-semibold text-text">
                {trafficCultureIndex.toFixed(1)}
              </span>
              {guAvgTrafficCultureIndex != null && (
                <span className="ml-1">/ 25구 평균 {guAvgTrafficCultureIndex.toFixed(1)}</span>
              )}
            </p>
          )}
          {hasTrafficRadar ? (
            <div className="h-[140px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={trafficRadarData}>
                  <PolarGrid stroke={CHART_COLORS.grid} />
                  <PolarAngleAxis
                    dataKey="subject"
                    tick={{ fontSize: 11, fill: CHART_COLORS.axis }}
                  />
                  <PolarRadiusAxis
                    angle={90}
                    domain={[0, 100]}
                    tick={{ fontSize: 9, fill: CHART_COLORS.axis }}
                    tickCount={6}
                  />
                  <Radar
                    name={gu_name}
                    dataKey="구"
                    stroke={CATEGORY_COLORS.transport}
                    fill={CATEGORY_COLORS.transport}
                    fillOpacity={0.25}
                    isAnimationActive={true}
                    animationDuration={1200}
                  />
                  <Radar
                    name="25구 평균"
                    dataKey="평균"
                    stroke={CHART_COLORS.axis}
                    fill={CHART_COLORS.axis}
                    fillOpacity={0.08}
                    strokeDasharray="4 4"
                    isAnimationActive={true}
                    animationDuration={1200}
                    animationBegin={300}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[140px] text-text-muted text-[12px]">
              교통문화지수 데이터가 없습니다
            </div>
          )}
          <p className="m-0 mt-1 text-[11px] text-text-subtle">
            국토교통부 교통문화지수 · 0~100점(높을수록 양호) · {trafficCultureDate || '연간'}
          </p>
        </Card>

        {/* GRDP 총액 */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            GRDP 총액
          </h3>
          <div className="flex items-center gap-2 mb-1">
            <p className="text-[12px] m-0 text-text-subtle">{gu_name}</p>
            {grdpRank != null && (
              <Badge variant="neutral" size="sm">
                {grdpRank}위 / 25구
              </Badge>
            )}
          </div>
          <p className="tabular m-0 text-[18px] font-semibold text-text leading-[1.1]">
            {grdpTotalJo != null ? `${grdpTotalJo.toFixed(1)}조원` : '-'}
          </p>
          {grdpDate && (
            <p className="m-0 mt-1 text-[11px] text-text-subtle">{grdpDate}</p>
          )}
        </Card>

        {/* GRDP 1인당 */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            1인당 GRDP
          </h3>
          <p className="tabular m-0 text-[18px] font-semibold text-text leading-[1.1]">
            {grdpPerCapita != null ? `${grdpPerCapita.toFixed(1)}백만원` : '-'}
          </p>
          {guAvgGrdpPerCapita != null && grdpPerCapita != null && (
            <p className="m-0 mt-1 text-[12px] text-text-muted">
              25구 평균 {guAvgGrdpPerCapita.toFixed(1)}백만원
              <span
                className={`ml-1 font-medium ${
                  grdpPerCapita >= guAvgGrdpPerCapita ? 'text-success' : 'text-danger'
                }`}
              >
                {grdpPerCapita >= guAvgGrdpPerCapita ? '▲' : '▼'}
                {Math.abs(grdpPerCapita - guAvgGrdpPerCapita).toFixed(1)}백만원
              </span>
            </p>
          )}
          {grdpInsight && (
            <span className="inline-flex items-center mt-1 px-2.5 py-1 rounded-full bg-primary-soft text-[13px] font-semibold text-primary">{grdpInsight}</span>
          )}
        </Card>
      </div>

      {/* Row 3: Green + Fire metrics */}
      <div className="grid grid-cols-4 gap-2">
        <MetricCard
          label="녹지 비율"
          value={greenRatio}
          guAvg={guAvgGreenRatio}
          unit="%"
          date={mDate(metrics, 'AREA_GREEN')}
          rank={rank(metrics, 'AREA_GREEN')}
          higherIsBetter={true}
          formatter={(n) => n.toFixed(1)}
          insight={greenInsight}
        />
        <MetricCard
          label="화재 발생"
          value={fireCount}
          guAvg={guAvgFireCount}
          unit="건"
          date={mDate(metrics, 'FIRE_COUNT')}
          rank={rank(metrics, 'FIRE_COUNT')}
          higherIsBetter={false}
        />
      </div>
    </div>
  );
}
