import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import {
  candidateFromScore,
  useCandidateRegions,
} from '@/features/candidates/lib/candidates';
import { recommendRegions } from '@/features/common/lib/api';
import type { RecommendationRegionCandidate } from '@/features/common/types/api';
import {
  loadRecommendationConditions,
  loadRecommendationResults,
  saveRecommendationResults,
} from '@/features/recommendation/lib/recommendation';
import type { RecommendationPriority } from '@/features/recommendation/lib/recommendation';

type RegionLevel = 'adong' | 'ldong';

export default function RecommendationResults() {
  const conditions = loadRecommendationConditions();
  const cachedResults = loadRecommendationResults(conditions);
  const { addCandidate, hasCandidate } = useCandidateRegions();

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

  return (
    <main className="min-h-screen bg-primary-soft text-text">
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
