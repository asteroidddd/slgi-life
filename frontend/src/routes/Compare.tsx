// Compare — side-by-side comparison of up to 3 adongs (SPEC 6.4).
//
// URL contract (SPEC 8): /compare?adongs=A,B,C
//
// Honest Compare (FINDING-101 + FINDING-106, 2026-05-03):
//   Final 4 rows:
//     1) 종합점수      — composite score (CompareItem.score, weighted)
//     2) 평균 월세      — CompareItem.rent_avg
//     3) 생활시설 점수  — AdongScore.score_amenity (0~100)
//     4) 교통 점수      — AdongScore.score_transit (0~100)
//
// Highlight rule (FINDING-106):
//   In each row, the best value(s) get a Pale Green background.
//   Ties: "동률" badge, no highlight.

import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { Badge, Button } from '@/components/ui';
import { useCompare, useAdongScores } from '@/hooks/useAdongs';
import { DEFAULT_WEIGHTS } from '@/types/api';
import type { CompareItem, AdongScore } from '@/types/api';

const MAX_SLUGS = 3;
const SCORE_TIE_EPSILON = 0.5;

function parseSlugs(raw: string | null): string[] {
  if (!raw) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const piece of raw.split(',')) {
    const slug = piece.trim();
    if (!slug || seen.has(slug)) continue;
    seen.add(slug);
    out.push(slug);
    if (out.length >= MAX_SLUGS) break;
  }
  return out;
}

export default function Compare() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const slugs = useMemo(
    () => parseSlugs(searchParams.get('adongs')),
    [searchParams]
  );

  const weights = DEFAULT_WEIGHTS;
  const compareQ = useCompare(slugs, weights, slugs.length > 0);
  const scoresQ = useAdongScores(weights);

  const isLoading = compareQ.isLoading || (slugs.length > 0 && scoresQ.isLoading);
  const isError = compareQ.isError || scoresQ.isError;
  const error = compareQ.error ?? scoresQ.error;

  const scoresBySlug = useMemo(() => {
    const map = new Map<string, AdongScore>();
    if (scoresQ.data) {
      for (const row of scoresQ.data) map.set(row.slug, row);
    }
    return map;
  }, [scoresQ.data]);

  const handleRemove = (slug: string) => {
    const next = slugs.filter((s) => s !== slug);
    if (next.length === 0) {
      const params = new URLSearchParams(searchParams);
      params.delete('adongs');
      setSearchParams(params, { replace: true });
    } else {
      const params = new URLSearchParams(searchParams);
      params.set('adongs', next.join(','));
      setSearchParams(params, { replace: true });
    }
  };

  const handleAddMore = () => {
    window.alert(
      '메인 지도에서 동네를 클릭한 뒤 "비교에 추가"를 눌러주세요.'
    );
  };

  return (
    <div className="min-h-screen bg-bg text-text">
      <h1 className="sr-only">동네 비교</h1>

      <main className="max-w-[1200px] mx-auto p-6" id="main">
        {slugs.length === 0 && <EmptyState onBack={() => navigate('/')} />}

        {slugs.length > 0 && isLoading && (
          <div className="py-8 px-6 text-center text-body-base text-text-muted tracking-normal" role="status">
            비교 정보를 불러오는 중…
          </div>
        )}

        {slugs.length > 0 && isError && (
          <div className="py-8 px-6 text-center text-danger flex flex-col items-center gap-3" role="alert">
            비교 정보를 불러오지 못했습니다.
            <span className="text-caption text-text-muted">
              {error instanceof Error ? error.message : '알 수 없는 오류'}
            </span>
            <div className="mt-2">
              <Button variant="secondary" size="md" onClick={() => navigate('/')}>
                지도로 돌아가기
              </Button>
            </div>
          </div>
        )}

        {slugs.length > 0 && compareQ.data && compareQ.data.adongs.length > 0 && (
          <CompareTable
            adongs={compareQ.data.adongs}
            scoresBySlug={scoresBySlug}
            onRemove={handleRemove}
            onAddMore={handleAddMore}
          />
        )}
      </main>
    </div>
  );
}

function EmptyState({ onBack }: { onBack: () => void }) {
  return (
    <div className="max-w-[480px] mx-auto mt-20 py-8 px-6 text-center flex flex-col items-center gap-4">
      <h1 className="text-section-heading leading-[1.15] font-semibold tracking-[-0.36px] text-text m-0">비교할 동네가 없어요</h1>
      <p className="text-body-base leading-[1.6] text-text-muted tracking-normal m-0">
        메인 지도에서 동네를 클릭한 뒤 <strong className="text-text font-medium">비교에 추가</strong> 버튼을
        누르면 이곳에 나란히 보여드릴게요.
      </p>
      <Button variant="secondary" size="md" onClick={onBack}>
        메인 지도로 가기
      </Button>
    </div>
  );
}

interface CompareTableProps {
  adongs: CompareItem[];
  scoresBySlug: Map<string, AdongScore>;
  onRemove: (slug: string) => void;
  onAddMore: () => void;
}

interface RowDecision {
  bestIdx: Set<number>;
  isTie: boolean;
}

function CompareTable({
  adongs,
  scoresBySlug,
  onRemove,
  onAddMore,
}: CompareTableProps) {
  const [shareNotice, setShareNotice] = useState<string | null>(null);

  const breakdown = useMemo(() => {
    return adongs.map((d) => {
      const row = scoresBySlug.get(d.slug);
      return {
        score_amenity: row?.score_amenity ?? NaN,
        score_transit: row?.score_transit ?? NaN,
      };
    });
  }, [adongs, scoresBySlug]);

  const scoreVals = useMemo(() => adongs.map((d) => d.score), [adongs]);
  const rentVals = useMemo(
    () => adongs.map((d) => (d.rent_converted_avg ?? NaN)),
    [adongs]
  );
  const amenityVals = useMemo(
    () => breakdown.map((b) => b.score_amenity),
    [breakdown]
  );
  const transitVals = useMemo(
    () => breakdown.map((b) => b.score_transit),
    [breakdown]
  );

  const scoreDecision = useMemo(
    () => decideRow(scoreVals, 'max', SCORE_TIE_EPSILON),
    [scoreVals]
  );
  const rentDecision = useMemo(
    () => decideRow(rentVals, 'min', 0),
    [rentVals]
  );
  const amenityDecision = useMemo(
    () => decideRow(amenityVals, 'max', SCORE_TIE_EPSILON),
    [amenityVals]
  );
  const transitDecision = useMemo(
    () => decideRow(transitVals, 'max', SCORE_TIE_EPSILON),
    [transitVals]
  );

  const topScoreIdx = useMemo(() => {
    if (adongs.length <= 1) return -1;
    if (scoreDecision.isTie) return -1;
    if (scoreDecision.bestIdx.size !== 1) return -1;
    return [...scoreDecision.bestIdx][0];
  }, [adongs.length, scoreDecision]);

  const handleShare = async () => {
    const url = window.location.href;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
        setShareNotice('비교 URL이 복사되었습니다.');
      } else {
        setShareNotice(`복사를 지원하지 않는 브라우저입니다: ${url}`);
      }
    } catch {
      setShareNotice('복사에 실패했어요. 주소창의 URL을 사용해주세요.');
    }
    window.setTimeout(() => setShareNotice(null), 3000);
  };

  return (
    <div className="bg-surface border border-border rounded-card overflow-hidden">
      <table className="w-full border-collapse font-[family-name:var(--font-family-base)] tracking-normal" role="table">
        <colgroup>
          <col className="w-[180px]" />
          {adongs.map((d) => (
            <col key={d.slug} />
          ))}
        </colgroup>
        <thead>
          <tr className="bg-surface-alt border-b border-divider">
            <th scope="col" className="py-4 px-5 text-left font-normal text-caption text-text-muted align-top">
              <span className="inline-block font-mono text-mono-label font-normal tracking-[0.26px] text-text-subtle uppercase">지표</span>
            </th>
            {adongs.map((adong, idx) => (
              <th key={adong.slug} scope="col" className="py-4 px-5 text-left font-normal text-caption text-text-muted align-top">
                <ColumnHeader
                  adong={adong}
                  isTopScore={idx === topScoreIdx && adongs.length > 1}
                  onRemove={() => onRemove(adong.slug)}
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <Row label="종합점수" decision={scoreDecision} showTie={adongs.length > 1}>
            {adongs.map((d, i) => (
              <CellTd key={d.slug} highlight={scoreDecision.bestIdx.has(i)}>
                <span className="tabular">{d.score.toFixed(1)}</span>
                <span className="text-caption text-text-muted font-normal"> / 100</span>
              </CellTd>
            ))}
          </Row>
          <Row
            label="평균 환산 월세"
            hint="낮을수록 좋음"
            decision={rentDecision}
            showTie={adongs.length > 1}
          >
            {adongs.map((d, i) => {
              const v = d.rent_converted_avg;
              if (v == null) {
                return (
                  <CellTd key={d.slug} highlight={false}>
                    <span className="text-text-subtle">—</span>
                  </CellTd>
                );
              }
              return (
                <CellTd key={d.slug} highlight={rentDecision.bestIdx.has(i)}>
                  <span className="tabular">{v}</span>
                  <span className="text-caption text-text-muted font-normal"> 만원</span>
                </CellTd>
              );
            })}
          </Row>
          <Row
            label="생활시설 점수"
            decision={amenityDecision}
            showTie={adongs.length > 1}
          >
            {breakdown.map((b, i) => (
              <CellTd
                key={adongs[i].slug}
                highlight={amenityDecision.bestIdx.has(i)}
              >
                <ScoreValue value={b.score_amenity} />
              </CellTd>
            ))}
          </Row>
          <Row
            label="교통 점수"
            decision={transitDecision}
            showTie={adongs.length > 1}
          >
            {breakdown.map((b, i) => (
              <CellTd
                key={adongs[i].slug}
                highlight={transitDecision.bestIdx.has(i)}
              >
                <ScoreValue value={b.score_transit} />
              </CellTd>
            ))}
          </Row>
        </tbody>
      </table>

      <div className="py-3 px-5 border-t border-divider bg-surface-alt flex flex-col gap-1" aria-label="데이터 출처">
        <p className="m-0 flex items-baseline gap-2 text-micro leading-[1.4] text-text-muted">
          <span className="font-mono text-mono-label tracking-[0.26px] text-text-subtle uppercase shrink-0">SCORES</span>
          <span className="tracking-normal text-text-muted">
            자체 산출 — 소상공인진흥공단 · 서울교통빅데이터 · 국토교통부 (2026-04 기준)
          </span>
        </p>
        <p className="m-0 flex items-baseline gap-2 text-micro leading-[1.4] text-text-muted">
          <span className="font-mono text-mono-label tracking-[0.26px] text-text-subtle uppercase shrink-0">RENT</span>
          <span className="tracking-normal text-text-muted">
            환산 월세 = 월세 + 보증금 × 0.005 (서울 평균 전환률 6%/년 가정).
            점수(score_rent)와 동일 공식. 국토부 실거래가 5개 구 적재 한정 — 그 외 동은 "—".
          </span>
        </p>
        <p className="m-0 mt-1 text-micro leading-[1.4] tracking-normal text-text-subtle">
          통학시간 · 자취생 비율 · 안전 지수 · 자취생 평점은 데이터 적재 전까지
          비교에서 제외되었습니다.
        </p>
      </div>

      <footer className="flex items-center gap-3 p-5 border-t border-border bg-surface" aria-label="비교 액션">
        {adongs.length < MAX_SLUGS && (
          <Button variant="secondary" size="md" onClick={onAddMore}>
            + 동네 추가하기
          </Button>
        )}
        <Button variant="secondary" size="md" onClick={handleShare}>
          공유
        </Button>
        {shareNotice && (
          <span className="text-caption text-text-muted tracking-normal ml-2" role="status">
            {shareNotice}
          </span>
        )}
      </footer>
    </div>
  );
}

interface ColumnHeaderProps {
  adong: CompareItem;
  isTopScore: boolean;
  onRemove: () => void;
}

function ColumnHeader({ adong, isTopScore, onRemove }: ColumnHeaderProps) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-col gap-1">
        <span className="text-caption text-text-muted font-normal">{adong.gu}</span>
        <span className="text-card-heading font-semibold leading-[1.2] tracking-[-0.28px] text-text">{adong.name}</span>
      </div>
      <div className="flex items-center gap-2">
        {isTopScore && (
          <Badge variant="success" size="sm">
            최고 점수
          </Badge>
        )}
        <button
          type="button"
          className="w-[var(--control-height-sm)] h-[var(--control-height-sm)] inline-flex items-center justify-center border border-border rounded-sm bg-surface text-text-muted cursor-pointer text-[18px] leading-none ml-auto transition-all duration-[120ms] ease-out hover:bg-danger-soft hover:border-danger hover:text-danger focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2"
          onClick={onRemove}
          aria-label={`${adong.name} 비교에서 제거`}
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>
    </div>
  );
}

function Row({
  label,
  hint,
  decision,
  showTie,
  children,
}: {
  label: string;
  hint?: string;
  decision: RowDecision;
  showTie: boolean;
  children: React.ReactNode;
}) {
  return (
    <tr className="border-b border-divider last:border-b-0">
      <th scope="row" className="py-4 px-5 text-left text-caption font-normal text-text-muted bg-surface-alt tracking-normal align-middle">
        <span className="inline-block align-middle">
          {label}
          {hint && (
            <span className="text-text-subtle" aria-hidden="true">
              {' '}
              ↓
            </span>
          )}
        </span>
        {hint && (
          <span className="block text-caption text-text-subtle tracking-normal mt-[2px]" aria-label={hint}>
            {hint}
          </span>
        )}
        {showTie && decision.isTie && (
          <span className="inline-block align-middle ml-2 py-[2px] px-[6px] border border-divider rounded-sm font-mono text-mono-label tracking-[0.26px] text-text-subtle uppercase bg-surface" aria-label="모든 동네 값이 같음">
            동률
          </span>
        )}
      </th>
      {children}
    </tr>
  );
}

function CellTd({
  highlight,
  children,
}: {
  highlight: boolean;
  children: React.ReactNode;
}) {
  return (
    <td
      className={`py-4 px-5 text-body-base text-text align-middle ${
        highlight ? 'font-medium bg-primary-soft' : ''
      }`}
    >
      {children}
    </td>
  );
}

function ScoreValue({ value }: { value: number }) {
  if (!Number.isFinite(value)) {
    return <span className="text-text-subtle">—</span>;
  }
  return (
    <>
      <span className="tabular">{value.toFixed(1)}</span>
      <span className="text-caption text-text-muted font-normal"> / 100</span>
    </>
  );
}

function decideRow(
  values: number[],
  direction: 'max' | 'min',
  epsilon: number
): RowDecision {
  const result: RowDecision = { bestIdx: new Set(), isTie: false };
  if (values.length === 0) return result;
  if (values.length === 1) return result;

  const finite = values.filter((v) => Number.isFinite(v));
  if (finite.length === 0) return result;

  let best = finite[0];
  for (let i = 1; i < finite.length; i += 1) {
    if (direction === 'max' ? finite[i] > best : finite[i] < best) {
      best = finite[i];
    }
  }

  const isWithin = (v: number) =>
    Number.isFinite(v) && Math.abs(v - best) <= epsilon;

  const allAgree =
    finite.length === values.filter((v) => Number.isFinite(v)).length &&
    finite.every(isWithin);
  if (allAgree && finite.length === values.length) {
    result.isTie = true;
    return result;
  }

  values.forEach((v, idx) => {
    if (isWithin(v)) result.bestIdx.add(idx);
  });
  return result;
}
