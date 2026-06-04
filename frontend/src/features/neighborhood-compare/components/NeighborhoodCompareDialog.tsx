import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';

import {
  candidateKey,
  type CandidateRegion,
} from '@/features/candidates/lib/candidates';
import { useAuth } from '@/features/common/contexts/AuthContext';
import { getNeighborhoodCommuteTime, getNeighborhoodComparison, getUniversityOptions } from '@/features/common/lib/api';
import type {
  NeighborhoodCompareItem,
  NeighborhoodCompareMetric,
  NeighborhoodCompareSection,
} from '@/features/common/types/api';

interface NeighborhoodCompareDialogProps {
  candidates: CandidateRegion[];
  onClose: () => void;
}

interface CompareDialogFrame {
  left: number;
  right: number;
  top: number;
}

const DASHBOARD_COMPARE_TOP = 20;
const DASHBOARD_FALLBACK_PADDING = 20;
const DASHBOARD_FALLBACK_MAX_WIDTH = 1280;

function fallbackCompareFrame(): CompareDialogFrame {
  if (typeof window === 'undefined') {
    return {
      left: DASHBOARD_FALLBACK_PADDING,
      right: DASHBOARD_FALLBACK_PADDING,
      top: DASHBOARD_COMPARE_TOP,
    };
  }
  const side = Math.max(
    DASHBOARD_FALLBACK_PADDING,
    Math.round((window.innerWidth - DASHBOARD_FALLBACK_MAX_WIDTH) / 2 + DASHBOARD_FALLBACK_PADDING),
  );
  return {
    left: side,
    right: side,
    top: DASHBOARD_COMPARE_TOP,
  };
}

function readCompareFrame(): CompareDialogFrame {
  if (typeof document === 'undefined') return fallbackCompareFrame();
  const mainCard = document.querySelector<HTMLElement>('[data-dashboard-main-card="true"]');
  const rect = mainCard?.getBoundingClientRect();
  if (!rect || rect.width <= 0) return fallbackCompareFrame();

  return {
    left: Math.round(rect.left),
    right: Math.max(DASHBOARD_FALLBACK_PADDING, Math.round(window.innerWidth - rect.right)),
    top: DASHBOARD_COMPARE_TOP,
  };
}

const SCORE_ROWS: Array<{
  key: keyof NeighborhoodCompareItem['scores'];
  rankKey: keyof NeighborhoodCompareItem['scores'];
  label: string;
}> = [
  { key: 'total', rankKey: 'rank_total', label: '종합' },
  { key: 'rent', rankKey: 'rank_rent', label: '부동산' },
  { key: 'transit', rankKey: 'rank_transit', label: '교통' },
  { key: 'amenity', rankKey: 'rank_amenity', label: '편의시설' },
  { key: 'safety', rankKey: 'rank_safety', label: '안전' },
];

const SECTION_ROWS: Array<{
  key: keyof NeighborhoodCompareItem['sections'];
  title: string;
  kicker: string;
}> = [
  { key: 'rent', title: '주거 비용', kicker: '부동산' },
  { key: 'transit', title: '교통 접근성', kicker: '교통' },
  { key: 'infra', title: '생활 인프라', kicker: '편의시설' },
  { key: 'safety', title: '안전 지표', kicker: '안전' },
];

function formatScore(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '-';
  return Math.round(value).toString();
}

function formatRank(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '';
  return `${Math.round(value)}위`;
}

function formatMetricValue(metric: NeighborhoodCompareMetric) {
  if (metric.value == null || metric.value === '') return '-';
  const value = typeof metric.value === 'number'
    ? Number.isInteger(metric.value)
      ? metric.value.toLocaleString()
      : metric.value.toFixed(1)
    : metric.value;
  return `${value}${metric.unit ?? ''}`;
}

function toneClass(tone: string | undefined) {
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

function clampScore(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, value));
}

function stringValue(value: unknown) {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value.toLocaleString();
  return '';
}

function numberValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function categoryLabel(item: Record<string, unknown>) {
  return stringValue(item.label)
    || stringValue(item.group_label)
    || stringValue(item.category)
    || stringValue(item.housing_type)
    || '항목';
}

function categoryValue(item: Record<string, unknown>) {
  const displayValue = stringValue(item.display_value);
  const displayUnit = stringValue(item.display_unit);
  if (displayValue) return `${displayValue}${displayUnit}`;
  const count = numberValue(item.count);
  if (count != null) return `${count.toLocaleString()}곳`;
  const ratio = numberValue(item.ratio);
  if (ratio != null) return `${ratio.toFixed(1)}%`;
  return '-';
}

function normalizeSchoolName(value: string) {
  return value.trim().replace(/\s+/g, ' ');
}

function formatDuration(minutes: number | null | undefined) {
  if (typeof minutes !== 'number' || !Number.isFinite(minutes)) return '정보 없음';
  const safeMinutes = Math.max(0, Math.round(minutes));
  const hours = Math.floor(safeMinutes / 60);
  const remain = safeMinutes % 60;
  if (hours <= 0) return `${remain}분`;
  if (remain === 0) return `${hours}시간`;
  return `${hours}시간 ${remain}분`;
}

export default function NeighborhoodCompareDialog({
  candidates,
  onClose,
}: NeighborhoodCompareDialogProps) {
  const { user } = useAuth();
  const candidateKeys = useMemo(() => candidates.map((candidate) => candidateKey(candidate.regionLevel, candidate.slug)), [candidates]);
  const candidateKeysHash = candidateKeys.join('|');
  const [selectedKeys, setSelectedKeys] = useState<[string, string]>(['', '']);
  const [selectedUniversityId, setSelectedUniversityId] = useState('');
  const [userSchoolDefaultApplied, setUserSchoolDefaultApplied] = useState(false);
  const [compareFrame, setCompareFrame] = useState<CompareDialogFrame>(() => fallbackCompareFrame());

  const universitiesQuery = useQuery({
    queryKey: ['users', 'universities'],
    queryFn: getUniversityOptions,
    staleTime: 300_000,
  });
  const queryItems = useMemo(
    () => candidates.map((candidate) => ({ regionLevel: candidate.regionLevel, slug: candidate.slug })),
    [candidates],
  );
  const comparisonQuery = useQuery({
    queryKey: ['neighborhood-compare', candidateKeysHash],
    queryFn: () => getNeighborhoodComparison(queryItems),
    enabled: candidates.length >= 2,
    staleTime: 300_000,
  });

  useEffect(() => {
    setUserSchoolDefaultApplied(false);
  }, [user?.id]);

  useEffect(() => {
    if (userSchoolDefaultApplied || selectedUniversityId || !user?.school) return;
    const schools = universitiesQuery.data?.schools ?? [];
    if (schools.length === 0) return;
    const userSchoolName = normalizeSchoolName(user.school);
    const matchedSchool = schools.find((school) => normalizeSchoolName(school.name) === userSchoolName);
    if (matchedSchool) setSelectedUniversityId(matchedSchool.id);
    setUserSchoolDefaultApplied(true);
  }, [
    selectedUniversityId,
    universitiesQuery.data?.schools,
    user?.school,
    userSchoolDefaultApplied,
  ]);

  useEffect(() => {
    const first = candidateKeys[0] ?? '';
    const second = candidateKeys.find((key) => key !== first) ?? '';
    setSelectedKeys(([left, right]) => {
      const nextLeft = candidateKeys.includes(left) ? left : first;
      const fallbackRight = candidateKeys.find((key) => key !== nextLeft) ?? second;
      const nextRight = candidateKeys.includes(right) && right !== nextLeft ? right : fallbackRight;
      return [nextLeft, nextRight];
    });
  }, [candidateKeysHash]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    let animationFrame = 0;
    const updateCompareFrame = () => {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = window.requestAnimationFrame(() => {
        setCompareFrame(readCompareFrame());
      });
    };
    updateCompareFrame();
    window.addEventListener('resize', updateCompareFrame);
    window.visualViewport?.addEventListener('resize', updateCompareFrame);
    return () => {
      window.cancelAnimationFrame(animationFrame);
      window.removeEventListener('resize', updateCompareFrame);
      window.visualViewport?.removeEventListener('resize', updateCompareFrame);
    };
  }, []);

  const compareItems = comparisonQuery.data?.items ?? [];
  const itemByKey = useMemo(() => new Map(compareItems.map((item) => [item.key, item])), [compareItems]);
  const left = itemByKey.get(selectedKeys[0]) ?? null;
  const right = itemByKey.get(selectedKeys[1]) ?? null;
  const canCompare = candidates.length >= 2;
  const leftCommuteQuery = useQuery({
    queryKey: ['neighborhood-compare', 'commute', selectedKeys[0], selectedUniversityId],
    queryFn: () => getNeighborhoodCommuteTime(left!.regionLevel, left!.slug, selectedUniversityId),
    enabled: !!left && !!selectedUniversityId,
    staleTime: 300_000,
  });
  const rightCommuteQuery = useQuery({
    queryKey: ['neighborhood-compare', 'commute', selectedKeys[1], selectedUniversityId],
    queryFn: () => getNeighborhoodCommuteTime(right!.regionLevel, right!.slug, selectedUniversityId),
    enabled: !!right && !!selectedUniversityId,
    staleTime: 300_000,
  });

  return (
    <div className="fixed inset-0 z-[1550] bg-black/30" role="dialog" aria-modal="true" aria-label="동네들 비교">
      <button type="button" className="absolute inset-0 cursor-default" aria-label="닫기" onClick={onClose} />
      <section
        className="absolute bottom-8 flex flex-col overflow-hidden rounded-card border border-border bg-surface text-text shadow-[0_0_44px_rgba(15,23,42,0.24)] dark:shadow-[0_0_48px_rgba(0,0,0,0.46)]"
        style={{
          left: compareFrame.left,
          right: compareFrame.right,
          top: compareFrame.top,
        }}
      >
        <header className="flex items-start justify-between gap-5 border-b border-border px-5 py-4">
          <div>
            <p className="m-0 text-[12px] font-bold text-primary">담은 동네</p>
            <h2 className="m-0 mt-1 text-[24px] font-bold leading-tight">동네들 비교</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="h-9 w-9 rounded-[8px] bg-surface-alt text-[20px] font-bold text-text-muted transition hover:text-text"
            aria-label="닫기"
          >
            ×
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {!canCompare ? (
            <EmptyState title="비교할 동네가 부족합니다" description="담은 동네가 2개 이상일 때 비교할 수 있습니다." />
          ) : comparisonQuery.isLoading ? (
            <EmptyState title="비교 정보를 불러오는 중입니다" description="대시보드 캐시에서 동네 정보를 확인하고 있습니다." />
          ) : comparisonQuery.isError ? (
            <EmptyState title="비교 정보를 불러오지 못했습니다" description="잠시 후 다시 시도해 주세요." />
          ) : left && right ? (
            <div className="grid gap-4">
              <CompareSelectors
                candidates={candidates}
                selectedKeys={selectedKeys}
                onChange={setSelectedKeys}
              />
              <div className="grid grid-cols-2 gap-4">
                <RegionHeaderCard item={left} />
                <RegionHeaderCard item={right} />
              </div>
              <ScoreComparison left={left} right={right} />
              {SECTION_ROWS.map((section) => (
                <DetailSection
                  key={section.key}
                  title={section.title}
                  kicker={section.kicker}
                  left={left.sections[section.key]}
                  right={right.sections[section.key]}
                >
                  {section.key === 'transit' ? (
                    <CommuteComparePanel
                      left={left}
                      right={right}
                      schools={universitiesQuery.data?.schools ?? []}
                      selectedUniversityId={selectedUniversityId}
                      universityLoading={universitiesQuery.isLoading}
                      leftMinutes={leftCommuteQuery.data?.travel_minutes ?? null}
                      rightMinutes={rightCommuteQuery.data?.travel_minutes ?? null}
                      leftPending={leftCommuteQuery.isFetching}
                      rightPending={rightCommuteQuery.isFetching}
                      leftError={leftCommuteQuery.isError}
                      rightError={rightCommuteQuery.isError}
                      onUniversityChange={setSelectedUniversityId}
                    />
                  ) : null}
                </DetailSection>
              ))}
            </div>
          ) : (
            <EmptyState title="비교할 수 있는 동네 정보가 없습니다" description="대시보드 캐시가 있는 다른 동네를 선택해 주세요." />
          )}
        </div>
      </section>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="grid min-h-[360px] place-items-center">
      <div className="max-w-[420px] rounded-card border border-dashed border-border bg-surface-alt px-5 py-6 text-center">
        <h3 className="m-0 text-[18px] font-bold">{title}</h3>
        <p className="m-0 mt-2 text-[13px] leading-6 text-text-muted">{description}</p>
      </div>
    </div>
  );
}

function CompareSelectors({
  candidates,
  selectedKeys,
  onChange,
}: {
  candidates: CandidateRegion[];
  selectedKeys: [string, string];
  onChange: (keys: [string, string]) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-4 rounded-card border border-border bg-surface-alt p-3">
      <RegionSelect
        label="왼쪽 동네"
        candidates={candidates}
        value={selectedKeys[0]}
        disabledKey={selectedKeys[1]}
        onChange={(value) => onChange([value, selectedKeys[1]])}
      />
      <RegionSelect
        label="오른쪽 동네"
        candidates={candidates}
        value={selectedKeys[1]}
        disabledKey={selectedKeys[0]}
        onChange={(value) => onChange([selectedKeys[0], value])}
      />
    </div>
  );
}

function CommuteComparePanel({
  left,
  right,
  schools,
  selectedUniversityId,
  universityLoading,
  leftMinutes,
  rightMinutes,
  leftPending,
  rightPending,
  leftError,
  rightError,
  onUniversityChange,
}: {
  left: NeighborhoodCompareItem;
  right: NeighborhoodCompareItem;
  schools: Array<{ id: string; name: string; school_type: string }>;
  selectedUniversityId: string;
  universityLoading: boolean;
  leftMinutes: number | null;
  rightMinutes: number | null;
  leftPending: boolean;
  rightPending: boolean;
  leftError: boolean;
  rightError: boolean;
  onUniversityChange: (universityId: string) => void;
}) {
  return (
    <div className="mt-4 grid grid-cols-[minmax(0,1fr)_280px_minmax(0,1fr)] items-center gap-4 border-t border-border pt-4">
      <CommuteBadge
        align="right"
        name={left.name}
        minutes={leftMinutes}
        enabled={!!selectedUniversityId}
        pending={leftPending}
        error={leftError}
      />
      <label className="grid gap-1.5 text-center">
        <span className="text-[12px] font-bold text-text-muted">대학 통학 시간</span>
        <select
          value={selectedUniversityId}
          onChange={(event) => onUniversityChange(event.target.value)}
          className="h-10 rounded-[8px] border border-border bg-surface px-3 text-[14px] font-bold text-text outline-none transition focus:border-primary"
        >
          <option value="">{universityLoading ? '대학 불러오는 중' : '대학 선택'}</option>
          {schools.map((school) => (
            <option key={school.id} value={school.id}>
              {school.name}
            </option>
          ))}
        </select>
      </label>
      <CommuteBadge
        align="left"
        name={right.name}
        minutes={rightMinutes}
        enabled={!!selectedUniversityId}
        pending={rightPending}
        error={rightError}
      />
    </div>
  );
}

function CommuteBadge({
  align,
  name,
  minutes,
  enabled,
  pending,
  error,
}: {
  align: 'left' | 'right';
  name: string;
  minutes: number | null;
  enabled: boolean;
  pending: boolean;
  error: boolean;
}) {
  let value = '-';
  if (enabled && pending) value = '확인 중';
  else if (enabled && error) value = '오류';
  else if (enabled) value = formatDuration(minutes);

  return (
    <div className={`min-w-0 ${align === 'right' ? 'text-right' : 'text-left'}`}>
      <span className="block truncate text-[12px] font-bold text-text-muted">{name}</span>
      <strong className="mt-1 block text-[20px] leading-none text-text">{value}</strong>
    </div>
  );
}

function RegionSelect({
  label,
  candidates,
  value,
  disabledKey,
  onChange,
}: {
  label: string;
  candidates: CandidateRegion[];
  value: string;
  disabledKey: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1.5">
      <span className="text-[12px] font-bold text-text-muted">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-[8px] border border-border bg-surface px-3 text-[14px] font-bold text-text outline-none transition focus:border-primary"
      >
        {candidates.map((candidate) => {
          const key = candidateKey(candidate.regionLevel, candidate.slug);
          return (
            <option key={key} value={key} disabled={key === disabledKey}>
              {candidate.gu} {candidate.name} · {candidate.regionLevel === 'adong' ? '행정동' : '법정동'}
            </option>
          );
        })}
      </select>
    </label>
  );
}

function RegionHeaderCard({ item }: { item: NeighborhoodCompareItem }) {
  const quicktakes = [
    ...item.sections.rent.quicktakes,
    ...item.sections.transit.quicktakes,
    ...item.sections.infra.quicktakes,
    ...item.sections.safety.quicktakes,
  ].slice(0, 5);

  return (
    <article className="rounded-card border border-border bg-surface-alt p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="m-0 text-[12px] font-bold text-primary">
            {item.gu} · {item.regionLevel === 'adong' ? '행정동' : '법정동'}
          </p>
          <h3 className="m-0 mt-1 truncate text-[28px] font-bold leading-tight">{item.name}</h3>
        </div>
        <div className="shrink-0 rounded-[10px] border border-border bg-surface px-3 py-2 text-center">
          <span className="block text-[11px] font-bold text-text-muted">종합</span>
          <strong className="block text-[24px] leading-none">{formatScore(item.scores.total)}</strong>
        </div>
      </div>
      <p className="m-0 mt-3 line-clamp-3 min-h-[72px] text-[14px] leading-6 text-text-muted">
        {item.intro || `${item.gu} ${item.name}의 생활 여건을 비교합니다.`}
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {quicktakes.length > 0 ? quicktakes.map((quicktake) => (
          <span key={`${quicktake.label}:${quicktake.tone}`} className={`rounded-full border px-2.5 py-1 text-[11px] font-bold ${toneClass(quicktake.tone)}`}>
            {quicktake.label}
          </span>
        )) : (
          <span className="text-[12px] font-semibold text-text-muted">요약 정보 없음</span>
        )}
      </div>
    </article>
  );
}

function ScoreComparison({ left, right }: { left: NeighborhoodCompareItem; right: NeighborhoodCompareItem }) {
  return (
    <section className="rounded-card border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="m-0 text-[12px] font-bold text-primary">점수</p>
          <h3 className="m-0 mt-0.5 text-[18px] font-bold">핵심 지표</h3>
        </div>
        <p className="m-0 text-[12px] font-semibold text-text-muted">100점에 가까울수록 유리합니다.</p>
      </div>
      <div className="grid gap-2">
        {SCORE_ROWS.map((row) => (
          <ScoreRow key={row.key} label={row.label} left={left} right={right} scoreKey={row.key} rankKey={row.rankKey} />
        ))}
      </div>
    </section>
  );
}

function ScoreRow({
  label,
  left,
  right,
  scoreKey,
  rankKey,
}: {
  label: string;
  left: NeighborhoodCompareItem;
  right: NeighborhoodCompareItem;
  scoreKey: keyof NeighborhoodCompareItem['scores'];
  rankKey: keyof NeighborhoodCompareItem['scores'];
}) {
  const leftScore = left.scores[scoreKey] as number | null;
  const rightScore = right.scores[scoreKey] as number | null;
  const leftRank = left.scores[rankKey] as number | null;
  const rightRank = right.scores[rankKey] as number | null;

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_78px_minmax(0,1fr)] items-center gap-3 rounded-[10px] bg-surface-alt px-3 py-2">
      <ScoreBar side="left" name={left.name} score={leftScore} rank={leftRank} />
      <span className="rounded-full border border-border bg-surface px-2 py-1 text-center text-[12px] font-bold text-text-muted">{label}</span>
      <ScoreBar side="right" name={right.name} score={rightScore} rank={rightRank} />
    </div>
  );
}

function ScoreBar({
  side,
  name,
  score,
  rank,
}: {
  side: 'left' | 'right';
  name: string;
  score: number | null;
  rank: number | null;
}) {
  return (
    <div className="min-w-0">
      <div className={`flex items-center justify-between gap-2 ${side === 'left' ? 'flex-row-reverse text-right' : ''}`}>
        <span className="truncate text-[12px] font-semibold text-text">{name}</span>
        <span className="shrink-0 text-[12px] font-bold tabular">
          {formatScore(score)}
          {formatRank(rank) ? <small className="ml-1 font-semibold text-text-muted">{formatRank(rank)}</small> : null}
        </span>
      </div>
      <div className={`mt-1 flex h-2 overflow-hidden rounded-full bg-surface ${side === 'left' ? 'justify-end' : 'justify-start'}`}>
        <div className="h-full rounded-full bg-primary" style={{ width: `${clampScore(score)}%` }} />
      </div>
    </div>
  );
}

function DetailSection({
  title,
  kicker,
  left,
  right,
  children,
}: {
  title: string;
  kicker: string;
  left: NeighborhoodCompareSection;
  right: NeighborhoodCompareSection;
  children?: ReactNode;
}) {
  return (
    <section className="rounded-card border border-border bg-surface p-4">
      <div className="mb-3">
        <p className="m-0 text-[12px] font-bold text-primary">{kicker}</p>
        <h3 className="m-0 mt-0.5 text-[18px] font-bold">{title}</h3>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <SectionColumn section={left} />
        <SectionColumn section={right} />
      </div>
      {children}
    </section>
  );
}

function SectionColumn({ section }: { section: NeighborhoodCompareSection }) {
  const showSafetyDetailCard = (section.grade_items?.length ?? 0) > 0 && section.metrics.length < 4;
  return (
    <article className="min-w-0 rounded-[10px] border border-border bg-surface-alt p-3">
      <div className="min-h-[86px] border-b border-border pb-3">
        <h4 className="m-0 text-[15px] font-bold leading-snug">{section.headline || '요약 정보 없음'}</h4>
        <p className="m-0 mt-1.5 text-[12px] leading-5 text-text-muted">{section.summary || '표시할 요약 문구가 없습니다.'}</p>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {section.metrics.slice(0, 4).map((metric) => (
          <MetricCard key={`${metric.key}:${metric.label}`} metric={metric} />
        ))}
        {showSafetyDetailCard ? <SafetyDetailCard items={section.grade_items ?? []} /> : null}
      </div>
      <ExtraList section={section} />
    </article>
  );
}

function MetricCard({ metric }: { metric: NeighborhoodCompareMetric }) {
  return (
    <div className="min-h-[92px] rounded-[8px] bg-surface p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="m-0 text-[11px] font-bold text-text-muted">{metric.label}</p>
        {metric.badge ? <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${toneClass(metric.tone)}`}>{metric.badge}</span> : null}
      </div>
      <strong className="mt-2 block text-[19px] leading-none tabular">{formatMetricValue(metric)}</strong>
      {metric.description ? <small className="mt-2 block text-[11px] font-semibold leading-4 text-text-muted">{metric.description}</small> : null}
    </div>
  );
}

function SafetyDetailCard({ items }: { items: Array<Record<string, unknown>> }) {
  return (
    <div className="min-h-[92px] rounded-[8px] bg-surface px-3 py-2.5">
      <p className="m-0 text-[11px] font-bold text-text-muted">안전 세부</p>
      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
        {items.slice(0, 6).map((item) => {
          const label = stringValue(item.label) || stringValue(item.key) || '항목';
          const value = stringValue(item.score) || stringValue(item.raw_value) || '-';
          return (
            <span key={`${label}:${value}`} className="flex min-w-0 items-baseline justify-between gap-1 text-[10px] leading-4">
              <span className="min-w-0 truncate font-bold text-text-muted">{label}</span>
              <strong className="shrink-0 text-[11px] leading-none text-text">{value}</strong>
            </span>
          );
        })}
      </div>
    </div>
  );
}

function ExtraList({ section }: { section: NeighborhoodCompareSection }) {
  const stationItems = section.station_items ?? [];
  const categoryItems = section.category_items ?? [];

  if (stationItems.length > 0) {
    return (
      <div className="mt-3 border-t border-border pt-3">
        <p className="m-0 text-[11px] font-bold text-text-muted">가까운 역</p>
        <div className="mt-2 grid gap-1.5">
          {stationItems.map((station) => (
            <span key={`${station.name}:${station.distance_m}`} className="flex items-center justify-between gap-2 text-[12px] font-semibold">
              <span className="truncate">{station.name ?? '-'}</span>
              <span className="shrink-0 text-text-muted">
                {typeof station.distance_m === 'number' ? `${Math.round(station.distance_m).toLocaleString()}m` : (station.lines ?? []).join(', ')}
              </span>
            </span>
          ))}
        </div>
      </div>
    );
  }

  if (categoryItems.length > 0) {
    return (
      <div className="mt-3 border-t border-border pt-3">
        <p className="m-0 text-[11px] font-bold text-text-muted">주요 시설</p>
        <div className="mt-2 grid grid-cols-2 gap-1.5">
          {categoryItems.slice(0, 4).map((item) => (
            <span key={`${categoryLabel(item)}:${categoryValue(item)}`} className="flex items-center justify-between gap-2 rounded-[7px] bg-surface px-2 py-1.5 text-[12px] font-semibold">
              <span className="truncate">{categoryLabel(item)}</span>
              <span className="shrink-0 text-text-muted">{categoryValue(item)}</span>
            </span>
          ))}
        </div>
      </div>
    );
  }

  return null;
}
