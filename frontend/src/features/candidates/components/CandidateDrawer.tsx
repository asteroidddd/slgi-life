import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import {
  type CandidateRegion,
  candidateDetailPath,
  candidateMapPath,
  useCandidateRegions,
} from '@/features/candidates/lib/candidates';

const CANDIDATE_DRAWER_COLLAPSED_KEY = 'candidate.drawer.collapsed';

function readCollapsed() {
  try {
    return window.localStorage.getItem(CANDIDATE_DRAWER_COLLAPSED_KEY) === 'true';
  } catch {
    return false;
  }
}

function formatScore(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '-';
  return Math.round(value).toString();
}

function sourceLabel(source: string) {
  if (source === 'conditions') return '추천';
  if (source === 'map') return '지도';
  return '동네 정보';
}

export function shouldShowCandidateDrawer(pathname: string) {
  return pathname === '/recommend/results'
    || pathname === '/map'
    || pathname.startsWith('/dashboard/');
}

export default function CandidateDrawer() {
  const navigate = useNavigate();
  const { candidates, removeCandidate, clearCandidates, maxCandidates } = useCandidateRegions();
  const [collapsed, setCollapsed] = useState(readCollapsed);

  useEffect(() => {
    try {
      window.localStorage.setItem(CANDIDATE_DRAWER_COLLAPSED_KEY, collapsed ? 'true' : 'false');
    } catch {
      // Storage may be blocked; current session state still works.
    }
  }, [collapsed]);

  const openCandidateOnMap = (candidate: CandidateRegion) => {
    const path = candidateMapPath(candidate);
    const separator = path.includes('?') ? '&' : '?';
    navigate(`${path}${separator}focus=${Date.now()}`);
  };

  return (
    <aside
      className={`fixed right-6 top-[126px] z-[1450] flex max-h-[calc(100vh-150px)] flex-col overflow-hidden rounded-card border border-border bg-surface/95 text-text shadow-floating backdrop-blur ${collapsed ? 'w-[190px]' : 'w-[292px]'}`}
      aria-label="담은 동네"
    >
      <header className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
        <div>
          <h2 className="m-0 text-[15px] font-bold">담은 동네</h2>
          <p className="m-0 mt-1 text-[11px] font-semibold text-text-muted">
            최대 {maxCandidates}개까지 저장
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {!collapsed && candidates.length > 0 ? (
            <button
              type="button"
              onClick={clearCandidates}
              className="h-7 rounded-[6px] bg-surface-alt px-2 text-[11px] font-bold text-text-muted transition hover:text-text"
            >
              비우기
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => setCollapsed((value) => !value)}
            className="h-7 rounded-[6px] bg-surface-alt px-2 text-[11px] font-bold text-text-muted transition hover:text-text"
            aria-expanded={!collapsed}
          >
            {collapsed ? '펼치기' : '접기'}
          </button>
        </div>
      </header>

      {collapsed ? null : (
        <>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {candidates.length === 0 ? (
          <div className="rounded-card border border-dashed border-border bg-surface-alt px-3 py-4 text-[12px] leading-5 text-text-muted">
            추천 결과나 지도에서 마음에 드는 동네를 담으면 여기에서 다시 볼 수 있습니다.
          </div>
        ) : (
          <div className="grid gap-2">
            {candidates.map((candidate) => (
              <article
                key={`${candidate.regionLevel}:${candidate.slug}`}
                className="rounded-card border border-border bg-surface-alt p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="m-0 text-[11px] font-bold text-primary">
                      {sourceLabel(candidate.source)} · {candidate.regionLevel === 'adong' ? '행정동' : '법정동'}
                    </p>
                    <h3 className="m-0 mt-1 truncate text-[15px] font-bold">
                      {candidate.gu} {candidate.name}
                    </h3>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeCandidate(candidate.regionLevel, candidate.slug)}
                    className="h-7 w-7 shrink-0 rounded-[6px] bg-surface text-[16px] leading-none text-text-muted transition hover:text-text"
                    aria-label={`${candidate.name} 후보에서 삭제`}
                    title="삭제"
                  >
                    ×
                  </button>
                </div>

                <div className="mt-3 grid grid-cols-4 gap-1.5">
                  <Metric label="부동산" value={candidate.score_rent} />
                  <Metric label="교통" value={candidate.score_transit} />
                  <Metric label="시설" value={candidate.score_amenity} />
                  <Metric label="안전" value={candidate.score_safety} />
                </div>

                <div className="mt-3 grid grid-cols-2 gap-2">
                  <Link
                    to={candidateDetailPath(candidate)}
                    className="inline-flex h-8 items-center justify-center rounded-[8px] bg-primary px-2 text-[12px] font-bold text-surface no-underline transition hover:bg-primary-hover hover:text-surface"
                  >
                    자세히 보기
                  </Link>
                  <button
                    type="button"
                    onClick={() => openCandidateOnMap(candidate)}
                    className="inline-flex h-8 items-center justify-center rounded-[8px] border border-border bg-surface px-2 text-[12px] font-bold text-text-muted no-underline transition hover:border-primary hover:bg-primary-soft hover:text-primary"
                  >
                    지도에서 보기
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
        </>
      )}
    </aside>
  );
}

function Metric({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="min-w-0 rounded-[7px] bg-surface px-2 py-1.5 text-center">
      <span className="block truncate text-[10px] font-bold text-text-muted">{label}</span>
      <strong className="mt-0.5 block text-[12px] leading-none">{formatScore(value)}</strong>
    </div>
  );
}
