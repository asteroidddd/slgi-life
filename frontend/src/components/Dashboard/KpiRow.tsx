// KpiRow -- dashboard top KPI rows.

import {
  Bar,
  BarChart,
  Line,
  LineChart,
  ResponsiveContainer,
} from 'recharts';

import { CHART_COLORS } from '@/lib/colors';
import type { AdongDetail, AdongScore } from '@/types/api';

import KpiCard from './KpiCard';

function computeAvgDeposit(
  bands: AdongDetail['real_estate']['deposit_band_avg'],
): number | null {
  if (!bands || bands.length === 0) return null;
  const bandMidpoints: Record<string, number> = {
    '0': 250,
    '500': 750,
    '1000': 1500,
    '2000': 2500,
    '3000+': 4000,
  };
  let totalWeight = 0;
  let weightedSum = 0;
  for (const b of bands) {
    const mid = bandMidpoints[b.band] ?? 1000;
    weightedSum += mid * b.avg_monthly_rent;
    totalWeight += b.avg_monthly_rent;
  }
  if (totalWeight === 0) return null;
  return Math.round(weightedSum / totalWeight);
}

function buildMiniLineData(
  trend: AdongDetail['real_estate']['monthly_trend'],
): Array<{ m: string; v: number }> {
  const last6 = trend.slice(-6);
  return last6.map((t) => {
    const vals = [t.villa, t.dagagu, t.danok, t.officetel].filter(
      (v): v is number => v != null,
    );
    return {
      m: t.month,
      v: vals.length > 0 ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : 0,
    };
  });
}

function buildMiniBarData(
  trend: AdongDetail['real_estate']['monthly_trend'],
): Array<{ m: string; v: number }> {
  const last6 = trend.slice(-6);
  return last6.map((t) => ({
    m: t.month,
    v: [t.villa, t.dagagu, t.danok, t.officetel].filter((v) => v != null).length,
  }));
}

function computeRentPercentile(
  allAdongs: AdongScore[] | undefined,
  rentValue: number,
): string | undefined {
  if (!allAdongs || allAdongs.length === 0) return undefined;
  const rents = allAdongs.map((d) => d.score_rent).sort((a, b) => b - a);
  const idx = rents.findIndex((r) => rentValue >= r);
  const percentile = idx >= 0 ? Math.max(1, Math.round(((idx + 1) / rents.length) * 100)) : 100;
  return `상위 ${percentile}%`;
}

function getDepositInsight(avgDeposit: number | null): string | undefined {
  if (avgDeposit == null) return undefined;
  if (avgDeposit <= 500) return '보증금 부담이 적은 동네예요';
  if (avgDeposit <= 1500) return '보증금이 평균 수준이에요';
  return '보증금이 다소 높은 편이에요';
}

interface KpiRowProps {
  detail: AdongDetail | undefined;
  allAdongs: AdongScore[] | undefined;
  isLoading: boolean;
}

export default function KpiRow({ detail, allAdongs, isLoading }: KpiRowProps) {
  const kpi = detail?.real_estate.studio_kpi;
  const avgDeposit = detail ? computeAvgDeposit(detail.real_estate.deposit_band_avg) : null;
  const miniLineData = detail ? buildMiniLineData(detail.real_estate.monthly_trend) : [];
  const miniBarData = detail ? buildMiniBarData(detail.real_estate.monthly_trend) : [];

  // Percentile computations for KPI cards
  const rentBadge = kpi?.avg_converted_rent != null
    ? computeRentPercentile(allAdongs, kpi.avg_converted_rent)
    : undefined;
  const rentInsight = kpi?.avg_converted_rent != null && allAdongs && allAdongs.length > 0
    ? `서울 ${allAdongs.length}개 동 중 월세가 ${(kpi.avg_converted_rent <= 50) ? '저렴한' : (kpi.avg_converted_rent <= 70) ? '평균 수준인' : '높은'} 편이에요`
    : undefined;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-3 gap-3">
        {/* 1. Average converted rent */}
        <KpiCard
          label="평균 환산 월세"
          value={
            kpi?.avg_converted_rent != null
              ? `${kpi.avg_converted_rent}만원`
              : '-'
          }
          badge={rentBadge}
          insight={rentInsight}
          hint="월세 + 보증금 x 0.005"
          isLoading={isLoading}
          miniChart={
            miniLineData.length > 0 ? (
              <div className="h-[32px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={miniLineData}>
                    <Line
                      type="monotone"
                      dataKey="v"
                      stroke={CHART_COLORS.villa}
                      strokeWidth={1.5}
                      dot={false}
                      isAnimationActive={true}
                      animationDuration={800}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : undefined
          }
        />

        {/* 2. Average deposit */}
        <KpiCard
          label="평균 보증금"
          value={avgDeposit != null ? `${avgDeposit.toLocaleString()}만원` : '-'}
          insight={getDepositInsight(avgDeposit)}
          hint="보증금 구간 가중평균"
          isLoading={isLoading}
        />

        {/* 3. Recent deal count */}
        <KpiCard
          label="최근 거래 건수"
          value={kpi?.recent_count != null ? `${kpi.recent_count}건` : '-'}
          insight={kpi?.recent_count != null ? '거래가 활발한 편이에요' : undefined}
          hint="최근 6개월 자취 거래"
          isLoading={isLoading}
          miniChart={
            miniBarData.length > 0 ? (
              <div className="h-[32px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={miniBarData}>
                    <Bar
                      dataKey="v"
                      fill={CHART_COLORS.dagagu}
                      radius={[2, 2, 0, 0]}
                      isAnimationActive={true}
                      animationDuration={800}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : undefined
          }
        />
      </div>
    </div>
  );
}
