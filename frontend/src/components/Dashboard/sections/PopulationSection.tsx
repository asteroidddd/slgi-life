// Dashboard PopulationSection -- SPEC 4.4 Section D (인구·사회).
//
// Widgets:
//   1. Gender ratio donut (adong_population latest male/female)
//   2. Population trend line (adong_population trend, 2022.09~)
//   3. Youth ratio highlight cards (POP_YOUTH_19_34 / POP_TOTAL_YOUTH_BASE)
//   4. Avg age card (POP_MEAN_AGE + male/female chips) — Phase 4 B1
//   5. 1-person household estimate donut (household vs population ratio)
//
// Data: AdongPopulationResponse + AdongGuMetricsResponse

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import { CATEGORY_COLORS, CHART_COLORS } from '@/lib/colors';
import type { AdongGuMetricsResponse, AdongPopulationResponse } from '@/types/api';

interface PopulationSectionProps {
  population: AdongPopulationResponse;
  guMetrics: AdongGuMetricsResponse | undefined;
}

const GENDER_COLORS = [CATEGORY_COLORS.transport, '#EC4899'] as const; // blue for male, pink for female

const TOOLTIP_STYLE = {
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  fontSize: 'var(--font-caption-size)',
};

/** Format ISO date "YYYY-MM-DD" → "YYYY년 기준". null/undefined → empty. */
function formatMetricDate(date: string | null | undefined): string {
  if (!date) return '';
  const year = date.slice(0, 4);
  return `${year}년 기준`;
}

/** Derive YoY insight text from the last 2+ years of change data. */
function getYoyInsight(yoyData: Array<{ year: string; change: number }>): string {
  if (yoyData.length < 2) return '인구 변동이 크지 않아요';
  const lastTwo = yoyData.slice(-2);
  const allNeg = lastTwo.every((d) => d.change < 0);
  const allPos = lastTwo.every((d) => d.change > 0);
  if (allNeg) return '최근 인구가 줄고 있어 유출 추세예요';
  if (allPos) return '최근 인구가 늘고 있어 유입 추세예요';
  return '인구 변동이 크지 않아요';
}

export default function PopulationSection({
  population,
  guMetrics,
}: PopulationSectionProps) {
  const latest = population.latest;
  const trend = population.trend;

  // 1. Gender ratio donut data
  const genderData = latest
    ? [
        { name: '남성', value: latest.male_population },
        { name: '여성', value: latest.female_population },
      ]
    : [];
  const maleRatio =
    latest && latest.total_population > 0
      ? ((latest.male_population / latest.total_population) * 100).toFixed(1)
      : null;
  const femaleRatio =
    latest && latest.total_population > 0
      ? ((latest.female_population / latest.total_population) * 100).toFixed(1)
      : null;

  // 2. Population YoY change data — group by year, compute year-over-year change rate
  const yoyData = (() => {
    if (trend.length < 2) return [];
    // Group by year, take the last entry per year
    const byYear = new Map<string, { pop: number; date: string }>();
    for (const row of trend) {
      const year = row.date.slice(0, 4);
      byYear.set(year, { pop: row.total_population, date: row.date });
    }
    const years = Array.from(byYear.keys()).sort();
    const result: Array<{ year: string; change: number }> = [];
    for (let i = 1; i < years.length; i++) {
      const prev = byYear.get(years[i - 1])!;
      const curr = byYear.get(years[i])!;
      if (prev.pop > 0) {
        result.push({
          year: years[i],
          change: +((((curr.pop - prev.pop) / prev.pop) * 100).toFixed(2)),
        });
      }
    }
    return result;
  })();

  // 3. Youth ratio — compute from POP_YOUTH_19_34/39 ÷ POP_TOTAL_YOUTH_BASE × 100.
  //    비교는 25구 평균값(gu_avg)으로 계산. SeoulMetric raw는 서울 전체 합계라
  //    동·구 단위 비교 의미가 약함.
  const youth19_34 = guMetrics?.metrics['POP_YOUTH_19_34']?.value ?? null;
  const youth19_39 = guMetrics?.metrics['POP_YOUTH_19_39']?.value ?? null;
  const youthBase = guMetrics?.metrics['POP_TOTAL_YOUTH_BASE']?.value ?? null;
  const guAvgYouth19_34 = guMetrics?.metrics['POP_YOUTH_19_34']?.gu_avg ?? null;
  const guAvgYouth19_39 = guMetrics?.metrics['POP_YOUTH_19_39']?.gu_avg ?? null;
  const guAvgYouthBase = guMetrics?.metrics['POP_TOTAL_YOUTH_BASE']?.gu_avg ?? null;
  const youthRank19_34 = guMetrics?.metrics['POP_YOUTH_19_34']?.rank_in_seoul ?? null;
  const youthRank19_39 = guMetrics?.metrics['POP_YOUTH_19_39']?.rank_in_seoul ?? null;

  const youthRatio19_34 =
    youth19_34 != null && youthBase != null && youthBase > 0
      ? (youth19_34 / youthBase) * 100
      : null;
  const youthRatio19_39 =
    youth19_39 != null && youthBase != null && youthBase > 0
      ? (youth19_39 / youthBase) * 100
      : null;
  const guAvgYouthRatio19_34 =
    guAvgYouth19_34 != null && guAvgYouthBase != null && guAvgYouthBase > 0
      ? (guAvgYouth19_34 / guAvgYouthBase) * 100
      : null;
  const guAvgYouthRatio19_39 =
    guAvgYouth19_39 != null && guAvgYouthBase != null && guAvgYouthBase > 0
      ? (guAvgYouth19_39 / guAvgYouthBase) * 100
      : null;
  const youthDate = formatMetricDate(guMetrics?.metrics['POP_YOUTH_19_34']?.date);

  // 4. (B1) Avg age — POP_MEAN_AGE / *_MALE / *_FEMALE (25구 평균 비교)
  const meanAge = guMetrics?.metrics['POP_MEAN_AGE']?.value ?? null;
  const meanAgeMale = guMetrics?.metrics['POP_MEAN_AGE_MALE']?.value ?? null;
  const meanAgeFemale = guMetrics?.metrics['POP_MEAN_AGE_FEMALE']?.value ?? null;
  const guAvgMeanAge = guMetrics?.metrics['POP_MEAN_AGE']?.gu_avg ?? null;
  const meanAgeRank = guMetrics?.metrics['POP_MEAN_AGE']?.rank_in_seoul ?? null;
  const meanAgeDate = formatMetricDate(guMetrics?.metrics['POP_MEAN_AGE']?.date);
  const meanAgeDiff = meanAge != null && guAvgMeanAge != null ? meanAge - guAvgMeanAge : null;

  // 6. 1-person household estimate (가구당 평균인원 기반 단순 추정)
  const avgPersonsPerHousehold =
    latest && latest.household_count > 0
      ? latest.total_population / latest.household_count
      : null;
  const singleHouseholdPct =
    avgPersonsPerHousehold != null
      ? Math.max(0, Math.min(100, Math.round((2 - avgPersonsPerHousehold) * 100)))
      : null;
  const singleDonutData =
    singleHouseholdPct != null
      ? [
          { name: '1인 가구 (추정)', value: singleHouseholdPct },
          { name: '기타 가구', value: 100 - singleHouseholdPct },
        ]
      : [];

  // Insight texts
  const yoyInsight = getYoyInsight(yoyData);

  const youthInsight =
    youthRatio19_34 != null && guAvgYouthRatio19_34 != null
      ? youthRatio19_34 > guAvgYouthRatio19_34
        ? '같은 또래 자취생이 많은 구예요'
        : '청년 비율이 서울 평균보다 낮아요'
      : null;

  const singleInsight =
    singleHouseholdPct != null
      ? singleHouseholdPct >= 50
        ? '1인 가구 비율이 높아 자취 인프라가 잘 갖춰져 있을 거예요'
        : '가족 세대가 많은 동네예요'
      : null;

  return (
    <div className="flex flex-col gap-2">
      {/* Row 1: Gender donut + Population trend */}
      <div className="grid grid-cols-4 gap-2">
        {/* 1. Gender ratio donut */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            남녀 비율
          </h3>
          {genderData.length > 0 ? (
            <div className="flex flex-col items-center">
              <div className="h-[160px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={genderData}
                      dataKey="value"
                      cx="50%"
                      cy="50%"
                      innerRadius="55%"
                      outerRadius="80%"
                      paddingAngle={2}
                      isAnimationActive={true}
                      animationDuration={1000}
                      animationBegin={200}
                    >
                      {genderData.map((_, idx) => (
                        <Cell key={idx} fill={GENDER_COLORS[idx]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      formatter={(value) => {
                        const v = value as number;
                        return [`${v.toLocaleString()}명`, ''];
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex items-center gap-4 text-micro text-text-muted">
                <span>
                  <span className="inline-block w-2 h-2 rounded-full mr-1" style={{ backgroundColor: GENDER_COLORS[0] }} />
                  남성 {maleRatio}%
                </span>
                <span>
                  <span className="inline-block w-2 h-2 rounded-full mr-1" style={{ backgroundColor: GENDER_COLORS[1] }} />
                  여성 {femaleRatio}%
                </span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[120px] text-text-muted text-micro">
              인구 데이터가 없습니다
            </div>
          )}
        </Card>

        {/* 2. Population YoY change bar */}
        <Card padding="md" className="col-span-3">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            인구 증감률 (전년 대비)
          </h3>
          {yoyData.length > 0 ? (
            <>
              <div className="h-[130px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={yoyData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                    <XAxis
                      dataKey="year"
                      tick={{ fontSize: 10, fill: CHART_COLORS.axis }}
                      tickFormatter={(y: string) => `${y}년`}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: CHART_COLORS.axis }}
                      tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v}%`}
                      width={48}
                    />
                    <ReferenceLine y={0} stroke={CHART_COLORS.axis} strokeWidth={1} />
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      formatter={(value) => {
                        const v = value as number;
                        return [`${v > 0 ? '+' : ''}${v.toFixed(2)}%`, '증감률'];
                      }}
                      labelFormatter={(label) => `${label}년`}
                    />
                    <Bar
                      dataKey="change"
                      radius={[4, 4, 0, 0]}
                      isAnimationActive={true}
                      animationDuration={800}
                    >
                      {yoyData.map((entry, idx) => (
                        <Cell
                          key={idx}
                          fill={entry.change >= 0 ? CATEGORY_COLORS.population : CATEGORY_COLORS.safety}
                          fillOpacity={0.8}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <span className="inline-flex items-center mt-1 px-2.5 py-1 rounded-full bg-primary-soft text-[13px] font-semibold text-primary">{yoyInsight}</span>
            </>
          ) : (
            <div className="flex items-center justify-center h-[130px] text-text-muted text-micro">
              추이 데이터가 없습니다
            </div>
          )}
          <p className="m-0 mt-2 text-[11px] text-text-subtle">
            출처: 주민등록인구 · 전년 대비 증감률
          </p>
        </Card>
      </div>

      {/* Row 2: Youth ratio + Avg age + 1-person household */}
      <div className="grid grid-cols-3 gap-2">
        {/* 3. Youth ratio cards */}
        <Card padding="md">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="m-0 text-[16px] leading-snug font-semibold text-text">
              청년 비율
            </h3>
            {guMetrics && (
              <Badge variant="neutral" size="sm">
                {guMetrics.gu_name} 단위
              </Badge>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            {/* 19~34세 */}
            <div className="p-3 rounded-card border border-divider bg-surface">
              <p className="text-micro m-0 mb-1 text-text-subtle">19~34세</p>
              <p className="tabular m-0 text-body-large font-semibold text-text leading-[1.1]">
                {youthRatio19_34 != null ? `${youthRatio19_34.toFixed(1)}%` : '-'}
              </p>
              {guAvgYouthRatio19_34 != null && youthRatio19_34 != null && (
                <p className="m-0 mt-1 text-micro text-text-muted">
                  25구 평균 {guAvgYouthRatio19_34.toFixed(1)}%
                  <span className={`ml-1 font-medium ${youthRatio19_34 > guAvgYouthRatio19_34 ? 'text-success' : 'text-danger'}`}>
                    {youthRatio19_34 > guAvgYouthRatio19_34 ? '▲' : '▼'}
                    {Math.abs(youthRatio19_34 - guAvgYouthRatio19_34).toFixed(1)}%p
                  </span>
                </p>
              )}
              {youthRank19_34 != null && (
                <p className="m-0 mt-1 text-[11px] text-text-subtle">25구 중 {youthRank19_34}위</p>
              )}
            </div>
            {/* 19~39세 */}
            <div className="p-3 rounded-card border border-divider bg-surface">
              <p className="text-micro m-0 mb-1 text-text-subtle">19~39세</p>
              <p className="tabular m-0 text-body-large font-semibold text-text leading-[1.1]">
                {youthRatio19_39 != null ? `${youthRatio19_39.toFixed(1)}%` : '-'}
              </p>
              {guAvgYouthRatio19_39 != null && youthRatio19_39 != null && (
                <p className="m-0 mt-1 text-micro text-text-muted">
                  25구 평균 {guAvgYouthRatio19_39.toFixed(1)}%
                  <span className={`ml-1 font-medium ${youthRatio19_39 > guAvgYouthRatio19_39 ? 'text-success' : 'text-danger'}`}>
                    {youthRatio19_39 > guAvgYouthRatio19_39 ? '▲' : '▼'}
                    {Math.abs(youthRatio19_39 - guAvgYouthRatio19_39).toFixed(1)}%p
                  </span>
                </p>
              )}
              {youthRank19_39 != null && (
                <p className="m-0 mt-1 text-[11px] text-text-subtle">25구 중 {youthRank19_39}위</p>
              )}
            </div>
          </div>
          {youthInsight && (
            <span className="inline-flex items-center mt-1 px-2.5 py-1 rounded-full bg-primary-soft text-[13px] font-semibold text-primary">{youthInsight}</span>
          )}
          {youthDate && (
            <p className="m-0 mt-1 text-[11px] text-text-subtle">{youthDate}</p>
          )}
          {!guMetrics && (
            <div className="flex items-center justify-center h-[60px] text-text-muted text-micro">
              구 지표 데이터를 불러오는 중...
            </div>
          )}
        </Card>

        {/* 4. (B1) Avg age */}
        <Card padding="md">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="m-0 text-[16px] leading-snug font-semibold text-text">
              평균 연령
            </h3>
            {guMetrics && (
              <Badge variant="neutral" size="sm">
                {guMetrics.gu_name} 단위
              </Badge>
            )}
          </div>
          {meanAge != null ? (
            <>
              <p className="tabular m-0 text-body-large font-semibold text-text leading-[1.1]">
                {meanAge.toFixed(1)}
                <span className="ml-1 text-[13px] font-medium text-text-muted">세</span>
              </p>
              <div className="flex items-center gap-2 mt-2">
                {meanAgeMale != null && (
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-micro font-medium"
                    style={{
                      backgroundColor: 'var(--color-info-soft)',
                      color: GENDER_COLORS[0],
                    }}
                  >
                    남 {meanAgeMale.toFixed(1)}
                  </span>
                )}
                {meanAgeFemale != null && (
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-micro font-medium"
                    style={{
                      backgroundColor: 'var(--color-danger-soft)',
                      color: GENDER_COLORS[1],
                    }}
                  >
                    여 {meanAgeFemale.toFixed(1)}
                  </span>
                )}
              </div>
              {guAvgMeanAge != null && meanAgeDiff != null && (
                <p className="m-0 mt-2 text-micro text-text-muted">
                  25구 평균 {guAvgMeanAge.toFixed(1)}세
                  <span className={`ml-1 font-medium ${meanAgeDiff <= 0 ? 'text-success' : 'text-danger'}`}>
                    {meanAgeDiff >= 0 ? '▲' : '▼'}
                    {Math.abs(meanAgeDiff).toFixed(1)}세
                  </span>
                </p>
              )}
              {meanAgeRank != null && (
                <p className="m-0 mt-1 text-[11px] text-text-subtle">25구 중 {meanAgeRank}위</p>
              )}
              {meanAgeDate && (
                <p className="m-0 mt-1 text-[11px] text-text-subtle">{meanAgeDate}</p>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-[80px] text-text-muted text-micro">
              평균 연령 데이터가 없습니다
            </div>
          )}
        </Card>

        {/* 5. 1-person household estimate */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            1인 가구 추정
          </h3>
          {singleDonutData.length > 0 ? (
            <div className="flex flex-col items-center">
              <div className="h-[140px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={singleDonutData}
                      dataKey="value"
                      cx="50%"
                      cy="50%"
                      innerRadius="55%"
                      outerRadius="80%"
                      paddingAngle={2}
                      isAnimationActive={true}
                      animationDuration={1000}
                      animationBegin={400}
                    >
                      <Cell fill={CATEGORY_COLORS.population} />
                      <Cell fill="var(--color-info-soft)" />
                    </Pie>
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      formatter={(value) => {
                        const v = value as number;
                        return [`${v}%`, ''];
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <p className="m-0 text-[13px] font-semibold text-text text-center tabular">
                {singleHouseholdPct}%
              </p>
              <p className="m-0 text-[11px] text-text-muted text-center">
                가구당 평균 {avgPersonsPerHousehold?.toFixed(2)}인
              </p>
              <p className="m-0 mt-1 text-[11px] text-text-subtle text-center">
                추정값 (인구/세대 기반)
              </p>
              {singleInsight && (
                <span className="inline-flex items-center mt-1 px-2.5 py-1 rounded-full bg-primary-soft text-[13px] font-semibold text-primary">{singleInsight}</span>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-[100px] text-text-muted text-micro">
              데이터가 없습니다
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
