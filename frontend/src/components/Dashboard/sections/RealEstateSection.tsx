// Dashboard RealEstateSection -- SPEC 4.4 Section A.
//
// KPI row (4-col): 지가변동률 + 주택수 (narrower)
// 4-col chart grid: 월세추이(col-span-2) + 유형분포 + 산점도 + 보증금대역
//
// Data: AdongDetail.real_estate + AdongGuMetricsResponse

import { Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';

import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import { CHART_COLORS } from '@/lib/colors';
import type { AdongDetail, AdongGuMetricsResponse } from '@/types/api';

type DealTypeKey = 'villa' | 'dagagu' | 'danok' | 'officetel';

const DEAL_TYPE_FILL: Record<DealTypeKey, string> = {
  villa: CHART_COLORS.villa,
  dagagu: CHART_COLORS.dagagu,
  danok: CHART_COLORS.danok,
  officetel: CHART_COLORS.officetel,
};

const DEAL_TYPE_LABEL: Record<DealTypeKey, string> = {
  villa: '연립다세대',
  dagagu: '다가구',
  danok: '단독',
  officetel: '오피스텔',
};

const TOOLTIP_STYLE = {
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  fontSize: 'var(--font-caption-size)',
};

const LABEL_STYLE = { color: 'var(--color-text)' };

interface RealEstateSectionProps {
  realEstate: AdongDetail['real_estate'];
  slug: string;
  guMetrics?: AdongGuMetricsResponse;
}

/** Format ISO date "YYYY-MM-DD" → "YYYY년 기준". */
function formatMetricDate(date: string | null | undefined): string {
  if (!date) return '';
  return `${date.slice(0, 4)}년 기준`;
}

export default function RealEstateSection({ realEstate, slug, guMetrics }: RealEstateSectionProps) {
  const trend = realEstate.monthly_trend;

  // Housing type distribution from type_avg (count per type)
  const typeDistribution = realEstate.type_avg
    .filter((t) => t.count > 0)
    .map((t) => ({
      name: t.label,
      value: t.count,
      dealType: t.deal_type as DealTypeKey,
    }));

  // Scatter by type
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

  // Deposit bands
  const bands = realEstate.deposit_band_avg.map((b) => ({
    band: formatBandLabel(b.band),
    monthly: b.avg_monthly_rent,
  }));

  // B5. 지가 변동률 (25구 평균 비교)
  const landPriceChange = guMetrics?.metrics['LAND_PRICE_CHANGE_RATE']?.value ?? null;
  const guAvgLandPriceChange = guMetrics?.metrics['LAND_PRICE_CHANGE_RATE']?.gu_avg ?? null;
  const landPriceRank = guMetrics?.metrics['LAND_PRICE_CHANGE_RATE']?.rank_in_seoul ?? null;
  const landPriceDate = formatMetricDate(guMetrics?.metrics['LAND_PRICE_CHANGE_RATE']?.date);

  // B6. 주택 수 (25구 평균 비교)
  const housingCount = guMetrics?.metrics['HOUSING_COUNT']?.value ?? null;
  const guAvgHousingCount = guMetrics?.metrics['HOUSING_COUNT']?.gu_avg ?? null;
  const housingRank = guMetrics?.metrics['HOUSING_COUNT']?.rank_in_seoul ?? null;
  const housingDate = formatMetricDate(guMetrics?.metrics['HOUSING_COUNT']?.date);

  // Real estate insight
  const avgRent = trend.length > 0 ? trend[trend.length - 1] : null;
  const latestVilla = avgRent?.villa;
  const latestOfficetel = avgRent?.officetel;
  const realEstateInsight = latestVilla != null || latestOfficetel != null
    ? latestVilla != null && latestVilla <= 50
      ? '월세 부담이 적은 동네예요'
      : latestVilla != null && latestVilla >= 80
        ? '월세가 다소 높은 편이에요'
        : '월세 수준이 평균적이에요'
    : undefined;

  return (
    <div className="flex flex-col gap-2">
      {/* Real estate insight */}
      {realEstateInsight && (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-primary-soft text-[13px] font-semibold text-primary">{realEstateInsight}</span>
      )}

      {/* B5+B6 KPI row — gu-level real estate signals */}
      {guMetrics && (landPriceChange != null || housingCount != null) && (
        <div className="grid grid-cols-2 gap-2">
          {/* B5. 지가 변동률 */}
          <Card padding="md">
            <div className="flex items-center gap-2 mb-1">
              <p className="text-[12px] m-0 text-text-subtle">지가 변동률</p>
              <Badge variant="neutral" size="sm">
                {guMetrics.gu_name}
              </Badge>
            </div>
            {landPriceChange != null ? (
              <>
                <p
                  className={`tabular m-0 text-[18px] font-semibold leading-[1.1] ${
                    landPriceChange >= 0 ? 'text-success' : 'text-danger'
                  }`}
                >
                  {landPriceChange >= 0 ? '▲' : '▼'}
                  {Math.abs(landPriceChange).toFixed(2)}%
                </p>
                {guAvgLandPriceChange != null && (
                  <p className="m-0 mt-1 text-[11px] text-text-muted">
                    25구 평균 {guAvgLandPriceChange >= 0 ? '+' : ''}
                    {guAvgLandPriceChange.toFixed(2)}%
                  </p>
                )}
                {landPriceRank != null && (
                  <p className="m-0 mt-0.5 text-[11px] text-text-subtle">25구 중 {landPriceRank}위</p>
                )}
                {landPriceDate && (
                  <p className="m-0 mt-0.5 text-[11px] text-text-subtle">{landPriceDate}</p>
                )}
              </>
            ) : (
              <p className="m-0 text-[12px] text-text-muted">데이터가 없습니다</p>
            )}
          </Card>

          {/* B6. 주택 수 */}
          <Card padding="md">
            <div className="flex items-center gap-2 mb-1">
              <p className="text-[12px] m-0 text-text-subtle">주택 수</p>
              <Badge variant="neutral" size="sm">
                {guMetrics.gu_name}
              </Badge>
            </div>
            {housingCount != null ? (
              <>
                <p className="tabular m-0 text-[18px] font-semibold text-text leading-[1.1]">
                  {Math.round(housingCount).toLocaleString()}
                  <span className="ml-1 text-[13px] font-medium text-text-muted">호</span>
                </p>
                {guAvgHousingCount != null && (
                  <p className="m-0 mt-1 text-[11px] text-text-muted">
                    25구 평균 {Math.round(guAvgHousingCount).toLocaleString()}호
                  </p>
                )}
                {housingRank != null && (
                  <p className="m-0 mt-0.5 text-[11px] text-text-subtle">25구 중 {housingRank}위</p>
                )}
                {housingDate && (
                  <p className="m-0 mt-0.5 text-[11px] text-text-subtle">{housingDate}</p>
                )}
              </>
            ) : (
              <p className="m-0 text-[12px] text-text-muted">데이터가 없습니다</p>
            )}
          </Card>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {/* 1. Monthly trend line chart */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            월별 평균 환산월세 추이
          </h3>
          <p className="text-[11px] m-0 mb-1 text-text-subtle">
            국토부 실거래가 · 비아파트 4종 · 만원
          </p>
          <div className="w-full h-[140px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="month"
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                  tickMargin={4}
                />
                <YAxis
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                  tickMargin={4}
                  width={36}
                />
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  labelStyle={LABEL_STYLE}
                  formatter={(value) => {
                    const v = value as number | null | undefined;
                    return v == null
                      ? (['-', ''] as [string, string])
                      : ([`${v}만원`, ''] as [string, string]);
                  }}
                />
                <Legend
                  verticalAlign="top"
                  height={24}
                  iconType="circle"
                  iconSize={6}
                  wrapperStyle={{ fontSize: 11 }}
                />
                <Line
                  type="monotone"
                  dataKey="villa"
                  name="연립다세대"
                  stroke={CHART_COLORS.villa}
                  strokeWidth={2}
                  connectNulls={false}
                  dot={{ r: 2 }}
                  activeDot={{ r: 3 }}
                  isAnimationActive={true}
                  animationDuration={1200}
                />
                <Line
                  type="monotone"
                  dataKey="dagagu"
                  name="다가구"
                  stroke={CHART_COLORS.dagagu}
                  strokeWidth={2}
                  connectNulls={false}
                  dot={{ r: 2 }}
                  activeDot={{ r: 3 }}
                  isAnimationActive={true}
                  animationDuration={1200}
                  animationBegin={100}
                />
                <Line
                  type="monotone"
                  dataKey="danok"
                  name="단독"
                  stroke={CHART_COLORS.danok}
                  strokeWidth={2}
                  connectNulls={false}
                  dot={{ r: 2 }}
                  activeDot={{ r: 3 }}
                  isAnimationActive={true}
                  animationDuration={1200}
                  animationBegin={200}
                />
                <Line
                  type="monotone"
                  dataKey="officetel"
                  name="오피스텔"
                  stroke={CHART_COLORS.officetel}
                  strokeWidth={2}
                  connectNulls={false}
                  dot={{ r: 2 }}
                  activeDot={{ r: 3 }}
                  isAnimationActive={true}
                  animationDuration={1200}
                  animationBegin={300}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* 2. Housing type distribution donut */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            주택 유형 분포
          </h3>
          <p className="text-[11px] m-0 mb-1 text-text-subtle">
            국토부 실거래가 · 최근 6개월
          </p>
          <div className="w-full h-[180px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={typeDistribution}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius="45%"
                  outerRadius="75%"
                  paddingAngle={2}
                  isAnimationActive={true}
                  animationBegin={200}
                  animationDuration={1000}
                >
                  {typeDistribution.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={DEAL_TYPE_FILL[entry.dealType] ?? CHART_COLORS.bar}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  formatter={(value, name) => {
                    const v = typeof value === 'number' ? value : Number(value);
                    return [`${v}건`, String(name)] as [string, string];
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={24}
                  iconType="circle"
                  iconSize={6}
                  wrapperStyle={{ fontSize: 10 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* 3. Area x converted rent scatter */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            면적 x 환산월세
          </h3>
          <p className="text-[11px] m-0 mb-1 text-text-subtle">
            국토부 실거래가 · 점 1개 = 거래 1건
          </p>
          <div className="w-full h-[120px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="면적"
                  unit="m²"
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 9 }}
                  tickMargin={4}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="환산월세"
                  unit="만원"
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 9 }}
                  tickMargin={4}
                  width={36}
                />
                <ZAxis range={[16, 16]} />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  contentStyle={TOOLTIP_STYLE}
                  labelStyle={LABEL_STYLE}
                  formatter={(value, name) => {
                    const v = typeof value === 'number' ? value : Number(value);
                    const n = String(name);
                    if (n === '면적') return [`${v}`, n] as [string, string];
                    if (n === '환산월세') return [`${v}`, n] as [string, string];
                    return [`${v}`, n] as [string, string];
                  }}
                />
                {(Object.keys(scatterByType) as DealTypeKey[]).map((type) => (
                  <Scatter
                    key={type}
                    name={DEAL_TYPE_LABEL[type]}
                    data={scatterByType[type]}
                    fill={DEAL_TYPE_FILL[type]}
                    fillOpacity={0.7}
                    isAnimationActive={true}
                    animationDuration={800}
                    animationBegin={300}
                  />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* 4. Deposit band distribution */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            보증금 대역별 평균 월세
          </h3>
          <p className="text-[11px] m-0 mb-1 text-text-subtle">
            국토부 실거래가 · 보증금 구간별 평균 월세 (만원)
          </p>
          <div className="w-full h-[120px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={bands}
                layout="vertical"
                margin={{ top: 4, right: 24, bottom: 0, left: 8 }}
              >
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                  tickMargin={4}
                />
                <YAxis
                  type="category"
                  dataKey="band"
                  stroke={CHART_COLORS.axis}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                  width={64}
                  tickMargin={4}
                />
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  labelStyle={LABEL_STYLE}
                  formatter={(value) => {
                    const v = typeof value === 'number' ? value : Number(value);
                    return [`${v}만원`, '평균 월세'] as [string, string];
                  }}
                />
                <Bar
                  dataKey="monthly"
                  fill={CHART_COLORS.bar}
                  radius={[0, 4, 4, 0]}
                  barSize={14}
                  isAnimationActive={true}
                  animationDuration={1000}
                  animationBegin={200}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Link
        to={`/adong/${slug}/explore`}
        className="self-end text-[12px] text-link hover:underline"
      >
        자세한 시세 탐색 →
      </Link>
    </div>
  );
}

function formatBandLabel(band: string): string {
  switch (band) {
    case '0':
      return '0~500만';
    case '500':
      return '500~1000만';
    case '1000':
      return '1000~2000만';
    case '2000':
      return '2000~3000만';
    case '3000+':
      return '3000만+';
    default:
      return band;
  }
}
