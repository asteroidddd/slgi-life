import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import {
  candidateFromScore,
  useCandidateRegions,
} from '@/features/candidates/lib/candidates';
import { useAuth } from '@/features/common/contexts/AuthContext';
import { recommendRegions } from '@/features/common/lib/api';
import type { RecommendationRegionCandidate } from '@/features/common/types/api';
import {
  loadRecommendationConditions,
  loadRecommendationResults,
  saveRecommendationResults,
} from '@/features/recommendation/lib/recommendation';
import type { RecommendationPriority } from '@/features/recommendation/lib/recommendation';

type RegionLevel = 'adong' | 'ldong';

const REGION_LEVEL_NOTICE_STORAGE_KEY = 'recommendation.region-level-notice.dismissedAt';
const REGION_LEVEL_NOTICE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

export default function RecommendationResults() {
  const conditions = loadRecommendationConditions();
  const cachedResults = loadRecommendationResults(conditions);
  const { addCandidate, hasCandidate } = useCandidateRegions();
  const { user, isLoading: authLoading } = useAuth();
  const [showRegionLevelNotice, setShowRegionLevelNotice] = useState(false);

  const resultsQuery = useQuery({
    queryKey: ['recommend', 'regions', conditions],
    queryFn: async () => {
      const result = await recommendRegions(conditions!);
      saveRecommendationResults(conditions!, result);
      return result;
    },
    enabled: !!conditions && !cachedResults,
    staleTime: 60_000,
  });

  const priority = conditions?.priority ?? 'budget';
  const results = cachedResults ?? resultsQuery.data ?? null;
  const loading = !cachedResults && resultsQuery.isLoading;
  const isError = !cachedResults && resultsQuery.isError;
  const adongs = results?.adongs ?? [];
  const ldongs = results?.ldongs ?? [];

  useEffect(() => {
    if (authLoading || user) {
      setShowRegionLevelNotice(false);
      return;
    }

    try {
      const dismissedAt = Number(window.localStorage.getItem(REGION_LEVEL_NOTICE_STORAGE_KEY) || 0);
      setShowRegionLevelNotice(!dismissedAt || Date.now() - dismissedAt >= REGION_LEVEL_NOTICE_TTL_MS);
    } catch {
      setShowRegionLevelNotice(true);
    }
  }, [authLoading, user]);

  const closeRegionLevelNotice = () => {
    setShowRegionLevelNotice(false);
  };

  const dismissRegionLevelNoticeForWeek = () => {
    try {
      window.localStorage.setItem(REGION_LEVEL_NOTICE_STORAGE_KEY, String(Date.now()));
    } catch {
      // Storage may be blocked. Closing still works for this screen.
    }
    setShowRegionLevelNotice(false);
  };

  return (
    <main className="min-h-screen bg-primary-soft text-text">
      {showRegionLevelNotice ? (
        <RegionLevelNotice
          onClose={closeRegionLevelNotice}
          onDismissForWeek={dismissRegionLevelNoticeForWeek}
        />
      ) : null}
      <section className="mx-auto grid w-full max-w-[1120px] gap-5 px-5 py-24 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="m-0 text-[32px] font-semibold leading-tight tracking-normal sm:text-section-heading">
              추천 동네
            </h1>
            <p className="m-0 mt-2 text-[14px] leading-6 text-text-muted">
              입력 조건을 통과한 동네를 {priority === 'budget' ? '예산이 낮은 순' : '통학 시간이 짧은 순'}으로 정렬했습니다.
            </p>
          </div>
        </div>

        {conditions ? (
          <section className="rounded-sm border border-border bg-surface p-5 shadow-floating">
            <h2 className="m-0 text-feature-heading font-semibold">입력 조건</h2>
            <div className="mt-4 grid gap-3 text-[13px] leading-6 text-text-muted sm:grid-cols-2 lg:grid-cols-4">
              <Condition label="예산" value={`보증금 ${conditions.deposit.toLocaleString()}만원 / 월세 ${conditions.monthlyRent.toLocaleString()}만원`} />
              <Condition label="집 크기" value={conditions.areaM2 ? `${conditions.areaM2.toLocaleString()}m²` : '상관없음'} />
              <Condition label="교통" value={`${conditions.universityName || '대학 미선택'} ${conditions.maxCommuteMinutes}분 이내`} />
              <Condition label="우선순위" value={conditions.priority === 'budget' ? '예산 우선' : '교통 우선'} />
            </div>
          </section>
        ) : (
          <section className="rounded-sm border border-border bg-surface p-5 shadow-floating">
            <p className="m-0 text-[14px] text-text-muted">저장된 조건이 없습니다. 조건 입력 후 다시 확인하세요.</p>
          </section>
        )}

        {isError ? (
          <section className="rounded-sm border border-danger/25 bg-danger-soft p-4 text-[13px] font-semibold leading-6 text-danger">
            조건 추천 결과를 불러오지 못했습니다. 조건 입력 화면에서 다시 시도해 주세요.
          </section>
        ) : null}

        {!loading && !isError && conditions && adongs.length + ldongs.length === 0 ? (
          <section className="rounded-sm border border-warning bg-warning-soft p-4 text-[13px] font-semibold leading-6 text-text">
            조건에 맞는 동네가 없습니다. 예산, 통학 시간, 선호 시설을 조금 넓혀 보세요.
          </section>
        ) : null}

        <div className="grid gap-5 lg:grid-cols-2">
          <ResultGroup
            title="법정동 후보"
            regionLevel="ldong"
            items={ldongs}
            loading={loading}
            priority={priority}
            onCandidateAdd={(item) => addCandidate(candidateFromScore(item, 'ldong', 'conditions'))}
            hasCandidate={(item) => hasCandidate('ldong', item.slug)}
          />
          <ResultGroup
            title="행정동 후보"
            regionLevel="adong"
            items={adongs}
            loading={loading}
            priority={priority}
            onCandidateAdd={(item) => addCandidate(candidateFromScore(item, 'adong', 'conditions'))}
            hasCandidate={(item) => hasCandidate('adong', item.slug)}
          />
        </div>
      </section>
    </main>
  );
}

function Condition({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="m-0 font-semibold text-text">{label}</p>
      <p className="m-0 mt-1">{value}</p>
    </div>
  );
}

function RegionLevelNotice({
  onClose,
  onDismissForWeek,
}: {
  onClose: () => void;
  onDismissForWeek: () => void;
}) {
  return (
    <div className="fixed inset-0 z-[1700] flex items-center justify-center bg-black/35 px-5" role="dialog" aria-modal="true" aria-labelledby="region-level-notice-title">
      <section className="w-full max-w-[560px] rounded-card border border-border bg-surface px-7 py-6 text-text shadow-2xl sm:px-8 sm:py-7">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="m-0 text-[12px] font-bold text-primary">추천 기준 안내</p>
            <h2 id="region-level-notice-title" className="m-0 mt-1 text-[20px] font-semibold leading-snug">
              행정동과 법정동을 함께 보여드려요
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="h-8 w-8 shrink-0 rounded-[8px] bg-surface-alt text-[18px] font-bold leading-none text-text-muted transition hover:text-text"
            aria-label="안내 닫기"
          >
            ×
          </button>
        </div>
        <p className="m-0 mt-6 text-[14px] leading-7 text-text-muted">
          행정동은 행정 서비스를 위한 생활권 단위라 크기가 비교적 고르고, 시설·교통·생활 여건을 비교하기 좋습니다. 법정동은 크기가 제각각이라 생활권 비교에는 불리할 수 있지만, 부동산 거래내역이 법정동 기준으로 기록되기 때문에 월세와 거래 흐름을 더 정확히 반영할 수 있습니다.
        </p>
        <p className="m-0 mt-4 text-[14px] leading-7 text-text-muted">
          그래서 추천 결과는 생활 여건을 보기 좋은 행정동과 부동산 정보를 보기 좋은 법정동을 나눠 보여드립니다.
        </p>
        <div className="mt-7 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={onDismissForWeek}
            className="h-10 rounded-sm border border-border bg-surface px-4 text-[13px] font-semibold text-text-muted transition hover:border-primary hover:text-primary"
          >
            일주일 동안 보지 않기
          </button>
          <button
            type="button"
            onClick={onClose}
            className="h-10 rounded-sm bg-primary px-4 text-[13px] font-semibold text-surface transition hover:bg-primary-hover"
          >
            확인
          </button>
        </div>
      </section>
    </div>
  );
}

function ResultGroup({
  title,
  regionLevel,
  items,
  loading,
  priority,
  onCandidateAdd,
  hasCandidate,
}: {
  title: string;
  regionLevel: RegionLevel;
  items: RecommendationRegionCandidate[];
  loading: boolean;
  priority: RecommendationPriority;
  onCandidateAdd: (item: RecommendationRegionCandidate) => void;
  hasCandidate: (item: RecommendationRegionCandidate) => boolean;
}) {
  return (
    <section className="rounded-sm border border-border bg-surface p-5 shadow-floating">
      <h2 className="m-0 text-feature-heading font-semibold">{title}</h2>
      <div className="mt-4 grid gap-3">
        {loading ? (
          <p className="m-0 text-[14px] text-text-muted">불러오는 중...</p>
        ) : null}
        {!loading && items.length === 0 ? (
          <p className="m-0 text-[14px] text-text-muted">표시할 후보가 없습니다.</p>
        ) : null}
        {items.map((item, index) => {
          const saved = hasCandidate(item);
          return (
            <article
              key={item.slug}
              className="grid gap-3 rounded-sm border border-border bg-surface-alt p-4 text-text transition hover:border-primary hover:bg-primary-soft"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="m-0 text-[12px] font-semibold text-primary">{index + 1}위</p>
                  <h3 className="m-0 mt-1 text-[18px] font-semibold leading-snug">
                    {item.gu} {item.name}
                  </h3>
                </div>
                <div className="text-right">
                  <p className="m-0 text-[12px] text-text-muted">{priority === 'transport' ? '통학 시간' : item.rent_metric_label}</p>
                  <p className="m-0 mt-1 text-[18px] font-semibold">{formatRecommendationMetric(item, priority)}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[12px] font-semibold text-text-muted">
                <span>부동산 점수 {formatScore(item.score_rent)}</span>
                <span>교통 점수 {formatScore(item.score_transit)}</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => onCandidateAdd(item)}
                  className={`h-9 rounded-sm border px-3 text-[12px] font-semibold transition ${
                    saved
                      ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]'
                      : 'border-border bg-surface text-text-muted hover:border-primary hover:text-primary'
                  }`}
                >
                  {saved ? '담김' : '후보에 담기'}
                </button>
                <Link
                  to={`/dashboard/${regionLevel}/${encodeURIComponent(item.slug)}`}
                  className="inline-flex h-9 items-center justify-center rounded-sm bg-primary px-3 text-[12px] font-semibold text-surface no-underline transition hover:bg-primary-hover hover:text-surface"
                >
                  자세히 보기
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function formatRecommendationMetric(item: RecommendationRegionCandidate, priority: RecommendationPriority) {
  if (priority === 'transport') {
    return typeof item.travel_minutes === 'number' ? `${Math.round(item.travel_minutes)}분` : '-';
  }
  if (typeof item.rent_metric === 'number') {
    return `${item.rent_metric.toFixed(item.rent_metric_label.includes('m²') ? 2 : 0)}만원`;
  }
  return '-';
}

function formatScore(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '-';
  return Math.round(value).toString();
}
