// PreferenceModal — 5번 비교로 가중치 자동 학습 (SPEC 6.5).
import { useEffect, useMemo, useState } from 'react';

import { Badge, Button, Modal } from '@/components/ui';
import { usePreferencePairs, useSubmitPreference } from '@/hooks/usePreference';
import type {
  PairCard,
  PreferenceWeightsResponse,
  SubmitComparison,
} from '@/types/api';

const TOTAL_PAIRS = 5;

export interface LearnedWeights {
  rent: number;
  amenity: number;
  transit: number;
}

export interface PreferenceModalProps {
  open: boolean;
  onClose: () => void;
  onComplete: (weights: LearnedWeights) => void;
}

function amenityVariant(label: PairCard['amenity_label']): 'success' | 'warning' | 'danger' {
  if (label === '충분') return 'success';
  if (label === '보통') return 'warning';
  return 'danger';
}

interface ComparisonCardProps {
  card: PairCard;
  side: 'left' | 'right';
  onPick: () => void;
}

function ComparisonCard({ card, side, onPick }: ComparisonCardProps) {
  return (
    <button
      type="button"
      className="flex flex-col gap-3 p-5 bg-surface border border-border rounded-card text-left cursor-pointer transition-all duration-[120ms] ease-out hover:border-secondary hover:bg-surface-alt active:translate-y-px focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2"
      onClick={onPick}
      aria-label={`${card.gu} ${card.name} 선택`}
      data-side={side}
    >
      <div className="flex flex-col gap-[2px]">
        <span className="text-caption text-text-muted tracking-normal">{card.gu}</span>
        <span className="text-card-heading font-semibold leading-[1.2] tracking-[-0.28px] text-text">{card.name}</span>
      </div>

      <dl className="flex flex-col gap-2 m-0">
        <div className="flex items-center justify-between gap-3">
          <dt className="text-caption text-text-muted tracking-normal inline-flex items-baseline gap-2">
            평균 환산 월세
            <span className="mono-label">보증금 환산</span>
          </dt>
          <dd className="m-0 text-body-base font-medium text-text tracking-normal tabular inline-flex items-center">
            {card.rent_converted != null
              ? `${card.rent_converted}만원`
              : `${card.rent_avg}만원`}
          </dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-caption text-text-muted tracking-normal">통학 시간</dt>
          <dd className="m-0 text-body-base font-medium text-text tracking-normal tabular inline-flex items-center">도보 {card.transit_min}분</dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-caption text-text-muted tracking-normal">편의시설</dt>
          <dd className="m-0 inline-flex items-center">
            <Badge variant={amenityVariant(card.amenity_label)}>
              {card.amenity_label}
            </Badge>
          </dd>
        </div>
      </dl>

      <span
        className="inline-flex items-center justify-center min-h-[var(--control-height-cta)] px-4 mt-2 bg-secondary text-surface rounded-md text-button font-semibold tracking-normal transition-all duration-[120ms] ease-out"
        aria-hidden="true"
      >
        이게 더 좋아요
      </span>
    </button>
  );
}

interface WeightRowProps {
  label: string;
  value: number;
  tone: 'rent' | 'amenity' | 'transit';
}

function WeightRow({ label, value }: WeightRowProps) {
  return (
    <div className="grid grid-cols-[80px_1fr_56px] items-center gap-3">
      <span className="text-caption text-text-muted tracking-normal">{label}</span>
      <div
        className="h-2 bg-surface border border-border rounded-full overflow-hidden"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        aria-label={`${label} 가중치 ${value}%`}
      >
        <span
          className="block h-full rounded-full bg-secondary transition-all duration-[300ms] ease-out"
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-right font-mono text-mono-label font-medium tracking-[0.26px] text-text tabular">{value}%</span>
    </div>
  );
}

interface ResultScreenProps {
  weights: PreferenceWeightsResponse;
  onConfirm: () => void;
}

function buildSummaryLine(weights: PreferenceWeightsResponse): string {
  const items: Array<{ key: 'rent' | 'amenity' | 'transit'; label: string; value: number }> = [
    { key: 'transit', label: '통학', value: weights.w_transit },
    { key: 'rent', label: '주거비', value: weights.w_rent },
    { key: 'amenity', label: '생활시설', value: weights.w_amenity },
  ];
  const sorted = [...items].sort((a, b) => b.value - a.value);
  const text = sorted.map((s) => `${s.label} ${s.value}%`).join(', ');
  return `${text}를 중요시하시네요`;
}

function ResultScreen({ weights, onConfirm }: ResultScreenProps) {
  const summary = buildSummaryLine(weights);
  return (
    <div className="flex flex-col gap-5 py-2">
      <p className="m-0 font-mono text-mono-label font-normal tracking-[0.26px] uppercase text-accent">학습 완료</p>
      <h3 className="m-0 text-card-heading font-semibold leading-[1.2] tracking-[-0.28px] text-text">{summary}</h3>
      <p className="m-0 text-caption text-text-muted tracking-normal">
        메인 지도에서 가중치가 자동으로 적용됩니다.
      </p>

      <div className="flex flex-col gap-3 p-4 bg-surface-alt rounded-card">
        <WeightRow label="통학" value={weights.w_transit} tone="transit" />
        <WeightRow label="주거비" value={weights.w_rent} tone="rent" />
        <WeightRow label="생활시설" value={weights.w_amenity} tone="amenity" />
      </div>

      <Button variant="primary" size="lg" fullWidth onClick={onConfirm}>
        메인 지도에서 확인하기
      </Button>
    </div>
  );
}

export default function PreferenceModal({
  open,
  onClose,
  onComplete,
}: PreferenceModalProps) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [comparisons, setComparisons] = useState<SubmitComparison[]>([]);
  const [resultWeights, setResultWeights] = useState<PreferenceWeightsResponse | null>(
    null
  );

  const pairsQuery = usePreferencePairs(TOTAL_PAIRS, open);
  const submitMutation = useSubmitPreference();

  useEffect(() => {
    if (open) return;
    setCurrentIdx(0);
    setComparisons([]);
    setResultWeights(null);
    submitMutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const pairs = pairsQuery.data?.pairs ?? [];
  const currentPair = pairs[currentIdx];
  const totalSteps = TOTAL_PAIRS;
  const stepNumber = Math.min(currentIdx + 1, totalSteps);
  const progressPct = (currentIdx / totalSteps) * 100;

  const finished = currentIdx >= totalSteps;

  useEffect(() => {
    if (!open || !finished || resultWeights) return;
    if (submitMutation.isPending) return;
    if (submitMutation.isError) return;

    if (comparisons.length === 0) {
      setResultWeights({ w_rent: 33, w_amenity: 33, w_transit: 34 });
      return;
    }

    submitMutation.mutate(comparisons, {
      onSuccess: (data) => setResultWeights(data),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, finished, comparisons, resultWeights]);

  const handlePick = (winnerSide: 'left' | 'right') => {
    if (!currentPair) return;
    const won =
      winnerSide === 'left' ? currentPair.left.slug : currentPair.right.slug;
    const lost =
      winnerSide === 'left' ? currentPair.right.slug : currentPair.left.slug;
    setComparisons((prev) => [...prev, { won, lost }]);
    setCurrentIdx((idx) => idx + 1);
  };

  const handleSkipPair = () => {
    setCurrentIdx((idx) => idx + 1);
  };

  const handleSkipAll = () => {
    onComplete({ rent: 33, amenity: 33, transit: 34 });
  };

  const handleConfirmResult = () => {
    if (!resultWeights) return;
    onComplete({
      rent: resultWeights.w_rent,
      amenity: resultWeights.w_amenity,
      transit: resultWeights.w_transit,
    });
  };

  const showingResult = resultWeights !== null;
  const showingSubmitSpinner = finished && !showingResult && submitMutation.isPending;
  const showingSubmitError = finished && !showingResult && submitMutation.isError;
  const showingPair = !finished && !showingResult && currentPair !== undefined;
  const showingPairsError = !pairsQuery.isLoading && pairsQuery.isError && !showingResult;
  const showingPairsLoading =
    pairsQuery.isLoading && !showingResult && !finished;

  const ariaLabel = useMemo(
    () => (showingResult ? '선호 학습 완료' : '선호 학습 — 동네 비교'),
    [showingResult]
  );

  return (
    <Modal
      open={open}
      onClose={onClose}
      ariaLabel={ariaLabel}
      ariaLabelledBy={showingPair ? 'pref-modal-question' : undefined}
      maxWidth={600}
      hideCloseButton
    >
      <div className="flex flex-col gap-4">
        {!showingResult && (
          <div className="flex items-center justify-between gap-3">
            <span className="font-mono text-mono-label font-normal tracking-[0.26px] text-text-subtle uppercase tabular">
              {stepNumber} / {totalSteps}
            </span>
            <button
              type="button"
              className="appearance-none bg-transparent border-none p-0 text-caption text-text-muted cursor-pointer tracking-normal transition-all duration-[120ms] ease-out hover:text-text focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2 focus-visible:rounded-sm"
              onClick={handleSkipAll}
            >
              건너뛰기
            </button>
          </div>
        )}

        {!showingResult && (
          <div
            className="w-full h-[6px] bg-surface-alt rounded-full overflow-hidden"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={totalSteps}
            aria-valuenow={currentIdx}
            aria-label="진행 상황"
          >
            <span
              className="block h-full bg-secondary rounded-full transition-all duration-200 ease-out"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        )}

        {showingPair && (
          <div className="flex flex-col gap-1 mt-2">
            <h2 id="pref-modal-question" className="m-0 text-feature-heading font-semibold leading-[1.3] text-text">
              어디가 더 끌리시나요?
            </h2>
            <p className="m-0 text-caption leading-[1.4] text-text-muted tracking-normal">실제 데이터 기반 비교 · 정답은 없어요</p>
          </div>
        )}

        {showingPairsLoading && (
          <div className="flex flex-col items-center gap-3 py-6 px-4 text-body-base text-text-muted tracking-normal text-center" role="status" aria-live="polite">
            비교 동네를 불러오는 중…
          </div>
        )}

        {showingPairsError && (
          <div className="flex flex-col items-center gap-3 py-6 px-4 text-body-base text-danger tracking-normal text-center" role="alert">
            비교 동네를 불러오지 못했습니다.
            <Button
              variant="secondary"
              size="sm"
              onClick={() => pairsQuery.refetch()}
            >
              다시 시도
            </Button>
          </div>
        )}

        {showingPair && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <ComparisonCard
                card={currentPair.left}
                side="left"
                onPick={() => handlePick('left')}
              />
              <ComparisonCard
                card={currentPair.right}
                side="right"
                onPick={() => handlePick('right')}
              />
            </div>

            <div className="flex justify-center mt-1">
              <button
                type="button"
                className="appearance-none bg-transparent border-none py-2 px-3 text-caption text-text-muted tracking-normal cursor-pointer rounded-sm transition-all duration-[120ms] ease-out hover:text-text hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2"
                onClick={handleSkipPair}
              >
                둘 다 별로예요 · 다음 비교
              </button>
            </div>
          </>
        )}

        {showingSubmitSpinner && (
          <div className="flex flex-col items-center gap-3 py-6 px-4 text-body-base text-text-muted tracking-normal text-center" role="status" aria-live="polite">
            결과를 분석 중…
          </div>
        )}

        {showingSubmitError && (
          <div className="flex flex-col items-center gap-3 py-6 px-4 text-body-base text-danger tracking-normal text-center" role="alert">
            가중치 추정에 실패했습니다.
            <span className="text-caption text-text-muted">
              {submitMutation.error instanceof Error
                ? submitMutation.error.message
                : '알 수 없는 오류'}
            </span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  submitMutation.reset();
                  submitMutation.mutate(comparisons, {
                    onSuccess: (data) => setResultWeights(data),
                  });
                }}
              >
                다시 시도
              </Button>
              <Button variant="ghost" size="sm" onClick={onClose}>
                닫기
              </Button>
            </div>
          </div>
        )}

        {showingResult && resultWeights && (
          <ResultScreen weights={resultWeights} onConfirm={handleConfirmResult} />
        )}
      </div>
    </Modal>
  );
}
