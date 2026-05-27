// Dashboard TransitSection -- SPEC 4.4 Section C (교통).
//
// Widgets:
//   1. Nearest subway stations TOP 3 (card list with line colors)
//   2. Bus stats (stop_count, route_count) as big number cards
//   3. Subway time-of-day congestion line (weekday / saturday / sunday)
//   4. Bus time-of-day congestion line (weekday / weekend)
//   5. Adong personality estimate (label + reason + pattern bars)
//
// Data: AdongDetail.transit + TransitCongestionResponse

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import { CATEGORY_COLORS, CHART_COLORS } from '@/lib/colors';
import type {
  CongestionPoint,
  AdongDetail,
  TransitCongestionResponse,
} from '@/types/api';

interface TransitSectionProps {
  transit: AdongDetail['transit'];
  congestion?: TransitCongestionResponse;
}

/** Map subway line string to CSS variable name for line color. */
function lineColor(line: string): string {
  const match = line.match(/^(\d)/);
  if (match) {
    return `var(--color-subway-${match[1]})`;
  }
  return 'var(--color-text-muted)';
}

const TOOLTIP_STYLE = {
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  fontSize: 'var(--font-caption-size)',
};

interface SubwayRow {
  hour: number;
  평일: number | null;
  토요일: number | null;
  일요일: number | null;
}

interface BusRow {
  hour: number;
  평일: number | null;
  주말: number | null;
}

function toHourMap(points: CongestionPoint[]): Map<number, number | null> {
  const m = new Map<number, number | null>();
  points.forEach((p) => m.set(p.hour, p.congestion));
  return m;
}

function mergeSubwayRows(by: TransitCongestionResponse['subway']['by_day']): SubwayRow[] {
  const wk = toHourMap(by.평일);
  const sa = toHourMap(by.토요일);
  const su = toHourMap(by.일요일);
  return Array.from({ length: 24 }, (_, h) => ({
    hour: h,
    평일: wk.get(h) ?? null,
    토요일: sa.get(h) ?? null,
    일요일: su.get(h) ?? null,
  }));
}

function mergeBusRows(by: TransitCongestionResponse['bus']['by_pattern']): BusRow[] {
  const wk = toHourMap(by.평일);
  const we = toHourMap(by.주말);
  return Array.from({ length: 24 }, (_, h) => ({
    hour: h,
    평일: wk.get(h) ?? null,
    주말: we.get(h) ?? null,
  }));
}

function personalityTone(label: TransitCongestionResponse['personality']['label']): {
  bg: string;
  accent: string;
} {
  switch (label) {
    case '주거 중심':
      return { bg: 'var(--color-primary-soft)', accent: CATEGORY_COLORS.amenity };
    case '상업·업무 중심':
      return { bg: 'var(--color-warning-soft)', accent: CATEGORY_COLORS.realestate };
    case '유동인구 많음':
      return { bg: 'var(--color-info-soft)', accent: CATEGORY_COLORS.population };
    default:
      return { bg: 'var(--color-primary-soft)', accent: 'var(--color-text-muted)' };
  }
}

function PatternBar({
  label,
  value,
  max,
  accent,
}: {
  label: string;
  value: number | null;
  max: number;
  accent: string;
}) {
  const pct = value != null && max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-baseline justify-between">
        <span className="text-[11px] text-text-muted">{label}</span>
        <span className="tabular text-[11px] font-medium text-text">
          {value != null ? value.toFixed(1) : '-'}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-divider overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: accent }}
        />
      </div>
    </div>
  );
}

function splitStationLines(line: string): string[] {
  return line
    .split(/\s*[\/,·]\s*/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function mergeStationsByName(
  stations: TransitSectionProps['transit']['nearest_stations'],
): Array<{ name: string; lines: string[]; walking_min: number; rank: number }> {
  const map = new Map<string, { lines: string[]; walking_min: number; rank: number }>();
  for (const st of stations) {
    if (st.name === '정보 없음') continue;
    const existing = map.get(st.name);
    const lines = splitStationLines(st.line);
    if (existing) {
      for (const line of lines) {
        if (!existing.lines.includes(line)) existing.lines.push(line);
      }
      if (st.walking_min < existing.walking_min) existing.walking_min = st.walking_min;
    } else {
      map.set(st.name, { lines, walking_min: st.walking_min, rank: st.rank });
    }
  }
  return Array.from(map.entries()).map(([name, data]) => ({
    name,
    lines: data.lines,
    walking_min: data.walking_min,
    rank: data.rank,
  }));
}

/** Transit insight: combine station proximity + bus count. */
function getTransitInsight(
  mergedStations: Array<{ walking_min: number }>,
  busRouteCount: number,
): string | undefined {
  const hasNearStation = mergedStations.length > 0 && mergedStations[0].walking_min <= 10;
  const hasManyBuses = busRouteCount >= 5;
  if (hasNearStation && hasManyBuses) return '대중교통 접근성이 좋은 편이에요';
  if (hasNearStation) return '지하철 접근성이 좋은 동네예요';
  if (hasManyBuses) return '버스 노선이 다양한 동네예요';
  if (mergedStations.length === 0) return '지하철역이 다소 먼 동네예요';
  return undefined;
}

export default function TransitSection({ transit, congestion }: TransitSectionProps) {
  const mergedStations = mergeStationsByName(transit.nearest_stations);
  const bus = transit.bus;

  // Congestion rows
  const subwayRows = congestion ? mergeSubwayRows(congestion.subway.by_day) : [];
  const busRows = congestion ? mergeBusRows(congestion.bus.by_pattern) : [];
  const hasSubwayCongestion =
    congestion != null &&
    subwayRows.some((r) => r.평일 != null || r.토요일 != null || r.일요일 != null);
  const busStopCount = congestion?.bus.stop_count ?? 0;
  const hasBusCongestion =
    congestion != null && busStopCount > 0 && busRows.some((r) => r.평일 != null || r.주말 != null);

  const stationLabel =
    congestion && congestion.subway.stations.length > 0
      ? congestion.subway.stations.map((s) => `${s.name}${s.line ? `(${splitStationLines(s.line).join(' / ')})` : ''}`).join(', ')
      : '';

  // Personality + pattern scores
  const personality = congestion?.personality;
  const tone = personalityTone(personality?.label ?? null);
  const patternMax = (() => {
    if (!personality) return 0;
    const vals = [
      personality.scores.morning_peak,
      personality.scores.midday,
      personality.scores.evening_peak,
      personality.scores.weekend,
    ].filter((v): v is number => v != null);
    return vals.length > 0 ? Math.max(...vals) : 0;
  })();

  const transitInsight = getTransitInsight(mergedStations, bus.route_count);

  return (
    <div className="flex flex-col gap-2">
      {/* Transit insight */}
      {transitInsight && (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-primary-soft text-[13px] font-semibold text-primary">{transitInsight}</span>
      )}

      <div className="grid grid-cols-3 gap-2">
        {/* 1. Nearest subway stations */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            가까운 지하철역 TOP 3
          </h3>
          <div className="flex flex-col gap-2">
            {mergedStations.map((st, idx) => {
              const isTop = idx === 0;
              return (
                <div
                  key={st.name}
                  className={`flex items-center gap-3 p-2 rounded-card border ${
                    isTop
                      ? 'border-primary/30 bg-primary-soft/30'
                      : 'border-divider bg-surface'
                  }`}
                >
                  <div
                    className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-[13px] font-semibold ${
                      isTop
                        ? 'bg-primary text-surface'
                        : 'bg-primary-soft text-text-muted'
                    }`}
                  >
                    {idx + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[13px] font-medium text-text">
                        {st.name}
                      </span>
                      {st.lines.map((line) => (
                        <span
                          key={line}
                          className="inline-flex items-center px-1 py-0.5 rounded-full text-[10px] text-surface font-medium"
                          style={{ backgroundColor: lineColor(line) }}
                        >
                          {line}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex-shrink-0 text-right">
                    <span className="tabular text-[13px] font-semibold text-text">
                      {st.walking_min}분
                    </span>
                    <span className="text-[11px] text-text-muted ml-1">도보</span>
                  </div>
                </div>
              );
            })}
            {mergedStations.length === 0 && (
              <div className="text-center text-text-muted text-[12px] py-4">
                인근 지하철역 데이터가 없습니다.
              </div>
            )}
          </div>
        </Card>

        {/* 2. Bus stats */}
        <Card padding="md">
          <p className="text-[12px] m-0 mb-1 text-text-subtle">버스 정류장</p>
          <p className="tabular m-0 text-[18px] font-semibold text-text leading-[1.1]">
            {bus.stop_count}
          </p>
          <p className="m-0 mt-0.5 text-[11px] text-text-muted">개소</p>
        </Card>
        <Card padding="md">
          <p className="text-[12px] m-0 mb-1 text-text-subtle">버스 노선</p>
          <p className="tabular m-0 text-[18px] font-semibold text-text leading-[1.1]">
            {bus.route_count}
          </p>
          <p className="m-0 mt-0.5 text-[11px] text-text-muted">개 노선</p>
        </Card>
      </div>

      {/* Row: 시간대 혼잡도 — 지하철 + 버스 라인 차트 */}
      <div className="grid grid-cols-2 gap-2">
        {/* 지하철 시간대 혼잡도 */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            지하철 시간대 혼잡도
          </h3>
          {hasSubwayCongestion ? (
            <div className="h-[140px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={subwayRows} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                  <XAxis
                    dataKey="hour"
                    type="number"
                    domain={[0, 23]}
                    ticks={[0, 6, 12, 18, 23]}
                    tick={{ fontSize: 9, fill: CHART_COLORS.axis }}
                    tickFormatter={(v: number) => `${v}시`}
                  />
                  <YAxis
                    tick={{ fontSize: 9, fill: CHART_COLORS.axis }}
                    tickFormatter={(v: number) => v.toFixed(0)}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    labelFormatter={(label) => `${label}시`}
                    formatter={(value, name) => {
                      if (value == null) return ['-', name];
                      const v = value as number;
                      return [v.toFixed(2), name];
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  <Line
                    name="평일"
                    type="monotone"
                    dataKey="평일"
                    stroke={CATEGORY_COLORS.transport}
                    strokeWidth={2}
                    dot={{ r: 1.5, fill: CATEGORY_COLORS.transport }}
                    activeDot={{ r: 4 }}
                    connectNulls
                    isAnimationActive
                    animationDuration={1200}
                  />
                  <Line
                    name="토요일"
                    type="monotone"
                    dataKey="토요일"
                    stroke={CHART_COLORS.warningDeep}
                    strokeWidth={1.5}
                    dot={false}
                    connectNulls
                    isAnimationActive
                    animationDuration={1200}
                    animationBegin={200}
                  />
                  <Line
                    name="일요일"
                    type="monotone"
                    dataKey="일요일"
                    stroke={CHART_COLORS.warning}
                    strokeWidth={1.5}
                    dot={false}
                    connectNulls
                    isAnimationActive
                    animationDuration={1200}
                    animationBegin={400}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[140px] text-text-muted text-[12px]">
              인근 지하철역 혼잡도 데이터가 부족합니다
            </div>
          )}
          <p className="m-0 mt-1 text-[11px] text-text-subtle">
            {stationLabel
              ? `서울교통공사 · 인근 ${congestion?.subway.stations.length ?? 0}개역 평균 — ${stationLabel}`
              : '서울교통공사 혼잡도'}
          </p>
        </Card>

        {/* 버스 시간대 혼잡도 */}
        <Card padding="md">
          <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
            버스 시간대 혼잡도
          </h3>
          {hasBusCongestion ? (
            <div className="h-[140px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={busRows} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                  <XAxis
                    dataKey="hour"
                    type="number"
                    domain={[0, 23]}
                    ticks={[0, 6, 12, 18, 23]}
                    tick={{ fontSize: 9, fill: CHART_COLORS.axis }}
                    tickFormatter={(v: number) => `${v}시`}
                  />
                  <YAxis
                    tick={{ fontSize: 9, fill: CHART_COLORS.axis }}
                    tickFormatter={(v: number) => v.toFixed(2)}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    labelFormatter={(label) => `${label}시`}
                    formatter={(value, name) => {
                      if (value == null) return ['-', name];
                      const v = value as number;
                      return [v.toFixed(3), name];
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  <Line
                    name="평일"
                    type="monotone"
                    dataKey="평일"
                    stroke={CATEGORY_COLORS.transport}
                    strokeWidth={2}
                    dot={{ r: 1.5, fill: CATEGORY_COLORS.transport }}
                    activeDot={{ r: 4 }}
                    connectNulls
                    isAnimationActive
                    animationDuration={1200}
                  />
                  <Line
                    name="주말"
                    type="monotone"
                    dataKey="주말"
                    stroke={CHART_COLORS.warningDeep}
                    strokeWidth={1.5}
                    dot={false}
                    connectNulls
                    isAnimationActive
                    animationDuration={1200}
                    animationBegin={200}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[140px] text-text-muted text-[12px]">
              {busStopCount === 0
                ? '동에 매핑된 버스 정류장 데이터가 부족합니다'
                : '버스 시간대 혼잡도 데이터가 없습니다'}
            </div>
          )}
          <p className="m-0 mt-1 text-[11px] text-text-subtle">
            {busStopCount > 0
              ? `서울교통빅데이터 · 동 내 ${busStopCount}개 정류장 평균 · 최근 60일`
              : '서울교통빅데이터'}
          </p>
        </Card>
      </div>

      {/* 동 성격 추정 카드 (full width) */}
      <Card padding="md" className={personality?.label == null ? 'opacity-70' : ''}>
        <div
          className="rounded-card p-3 flex flex-col gap-2"
          style={{ backgroundColor: tone.bg }}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex flex-col gap-0.5">
              <p className="text-[12px] m-0 text-text-subtle">동 성격 추정</p>
              <p
                className="m-0 text-[18px] font-semibold leading-[1.2]"
                style={{ color: personality?.label != null ? tone.accent : 'var(--color-text-muted)' }}
              >
                {personality?.label ?? '특징 추정 보류'}
              </p>
              {personality?.reason && (
                <p className="m-0 mt-0.5 text-[12px] text-text-muted max-w-[640px]">
                  {personality.reason}
                </p>
              )}
              {personality?.label == null && !personality?.reason && (
                <p className="m-0 mt-0.5 text-[12px] text-text-muted">
                  혼잡도 패턴이 뚜렷한 특징을 보이지 않습니다
                </p>
              )}
            </div>
            <Badge variant="neutral" size="sm">
              혼잡도 패턴 기반
            </Badge>
          </div>

          {/* Pattern score bars */}
          {personality && (
            <div className="grid grid-cols-4 gap-2">
              <PatternBar
                label="출근 (7~9시)"
                value={personality.scores.morning_peak}
                max={patternMax}
                accent={tone.accent}
              />
              <PatternBar
                label="낮 (11~14시)"
                value={personality.scores.midday}
                max={patternMax}
                accent={tone.accent}
              />
              <PatternBar
                label="퇴근 (18~20시)"
                value={personality.scores.evening_peak}
                max={patternMax}
                accent={tone.accent}
              />
              <PatternBar
                label="주말 평균"
                value={personality.scores.weekend}
                max={patternMax}
                accent={tone.accent}
              />
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
