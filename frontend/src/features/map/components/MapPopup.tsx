import type { ScoreLayerKey } from '@/features/map/components/HeatMap';
import { formatManwonAmount } from '@/features/real-estate/lib/rent';
import type { AdongScore, MapSearchItem, RentDealPin } from '@/features/common/types/api';

export type SelectedPopup =
  | { type: 'adong'; adong: AdongScore }
  | { type: 'deal'; key: string; pins: RentDealPin[] }
  | { type: 'deal_loading'; key: string }
  | { type: 'facility'; title: string; description: string }
  | { type: 'home'; address?: string | null }
  | { type: 'search'; item: MapSearchItem }
  | null;

function MapPopup({
  popup,
  onClose,
  heatLayer,
  ranks,
  rankTotal,
  onRegionDashboardOpen,
  onRegionCandidateAdd,
}: {
  popup: SelectedPopup;
  onClose: () => void;
  heatLayer: ScoreLayerKey;
  ranks: ScoreRanks;
  rankTotal: number;
  onRegionDashboardOpen?: (adong: AdongScore) => void;
  onRegionCandidateAdd?: (adong: AdongScore) => void;
}) {
  if (!popup) return null;
  if (popup.type === 'adong') {
    const { adong } = popup;
    return (
      <article className="absolute left-1/2 top-1/2 z-[550] w-[360px] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-[8px] border border-border bg-surface shadow-xl">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <p className="m-0 text-[12px] font-semibold text-text-muted">{adong.gu}</p>
            <h2 className="m-0 text-[20px] font-semibold text-text">{adong.name}</h2>
          </div>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
        </header>
        <div className="grid gap-3 p-4">
          <div className="grid grid-cols-2 gap-2">
            <Metric label="종합" value={adong.score} rank={ranks.composite[adong.code]} rankTotal={rankTotal} active={heatLayer === 'composite'} className="col-span-2" />
            <Metric label="부동산" value={adong.score_rent} rank={ranks.rent[adong.code]} rankTotal={rankTotal} active={heatLayer === 'rent'} />
            <Metric label="교통" value={adong.score_transit} rank={ranks.transit[adong.code]} rankTotal={rankTotal} active={heatLayer === 'transit'} />
            <Metric label="편의시설" value={adong.score_amenity} rank={ranks.amenity[adong.code]} rankTotal={rankTotal} active={heatLayer === 'amenity'} />
            <Metric label="안전" value={adong.score_safety} rank={ranks.safety[adong.code]} rankTotal={rankTotal} active={heatLayer === 'safety'} />
          </div>
          <div className="grid grid-cols-2 gap-2">
          {onRegionCandidateAdd ? (
            <button
              type="button"
              onClick={() => onRegionCandidateAdd(adong)}
              className="h-10 rounded-sm border border-border bg-surface px-4 text-[13px] font-semibold text-text-muted transition hover:border-primary hover:bg-primary-soft hover:text-primary"
            >
              후보에 담기
            </button>
          ) : null}
          {onRegionDashboardOpen ? (
            <button
              type="button"
              onClick={() => onRegionDashboardOpen(adong)}
              className="h-10 rounded-sm bg-primary px-4 text-[13px] font-semibold text-surface transition hover:bg-primary-hover"
            >
              이 동네 더 자세히 보기
            </button>
          ) : null}
          </div>
        </div>
      </article>
    );
  }
  if (popup.type === 'deal') {
    const first = popup.pins[0];
    const address = [first.gu, first.dong_name, first.jibun].filter(Boolean).join(' ') || '주소 정보 없음';
    const deals = [...popup.pins].sort((a, b) => b.date.localeCompare(a.date));
    return (
      <article className="absolute left-1/2 top-1/2 z-[550] w-[380px] -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-surface p-4 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="m-0 text-[12px] font-semibold text-text-muted">주소</p>
            <h2 className="m-0 text-[18px] font-semibold text-text">{address}</h2>
            <p className="mt-1 text-[12px] font-semibold text-text-subtle">{deals.length > 1 ? `${deals.length}건 거래` : deals[0]?.date}</p>
          </div>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
        </div>
        <div className="mt-3 max-h-[260px] overflow-y-auto pr-1">
          {deals.map((deal) => (
            <div key={deal.id} className="mb-2 rounded-card border border-border bg-surface-alt p-3 last:mb-0">
              <p className="m-0 text-[12px] font-semibold text-text-muted">{deal.date}</p>
              <div className="mt-2 grid grid-cols-3 gap-2">
                <AmountMetric label="보증금" value={deal.deposit} />
                <AmountMetric label="월세" value={deal.monthly_rent} />
                <Metric label="면적" value={Math.round(deal.area_m2)} suffix="m²" />
              </div>
            </div>
          ))}
        </div>
      </article>
    );
  }
  if (popup.type === 'deal_loading') {
    return (
      <article className="absolute left-1/2 top-1/2 z-[550] w-[320px] -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-surface p-4 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="m-0 text-[12px] font-semibold text-text-muted">거래 상세</p>
            <h2 className="m-0 text-[18px] font-semibold text-text">불러오는 중...</h2>
          </div>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
        </div>
      </article>
    );
  }
  if (popup.type === 'search') {
    return (
      <article className="absolute left-1/2 top-1/2 z-[550] w-[320px] -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-surface p-4 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="m-0 text-[12px] font-semibold text-text-muted">{popup.item.label}</p>
            <h2 className="m-0 text-[18px] font-semibold text-text">{popup.item.name}</h2>
            {popup.item.address ? <p className="mt-2 text-[13px] leading-5 text-text-muted">{popup.item.address}</p> : null}
          </div>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
        </div>
      </article>
    );
  }
  if (popup.type === 'home') {
    return (
      <article className="absolute left-1/2 top-1/2 z-[550] w-[320px] -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-surface p-4 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="m-0 text-[12px] font-semibold text-text-muted">내 집</p>
            <h2 className="m-0 text-[18px] font-semibold text-text">저장된 집 위치</h2>
            {popup.address ? <p className="mt-2 text-[13px] leading-5 text-text-muted">{popup.address}</p> : null}
          </div>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
        </div>
      </article>
    );
  }
  return (
    <article className="absolute left-1/2 top-1/2 z-[550] w-[320px] -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-surface p-4 shadow-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="m-0 text-[18px] font-semibold text-text">{popup.title}</h2>
          <p className="mt-2 text-[13px] leading-5 text-text-muted">{popup.description}</p>
        </div>
        <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px]">×</button>
      </div>
    </article>
  );
}

function Metric({ label, value, suffix = '', active = false, rank, rankTotal, className = '' }: { label: string; value: number | null | undefined; suffix?: string; active?: boolean; rank?: number; rankTotal?: number; className?: string }) {
  return (
    <div className={`rounded-card border p-3 ${active ? 'border-[var(--color-heatmap-4)] bg-[var(--color-heatmap-1)]' : 'border-border bg-surface-alt'} ${className}`}>
      <p className="m-0 text-[12px] font-semibold text-text-muted">{label}</p>
      <strong className="mt-1 block text-[20px] text-text">{typeof value === 'number' && Number.isFinite(value) ? Math.round(value) : '-'}{suffix}</strong>
      {rank && rankTotal ? <span className="mt-1 block text-[11px] font-semibold text-text-subtle">순위 {rank}/{rankTotal}</span> : null}
    </div>
  );
}

function AmountMetric({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="rounded-card border border-border bg-surface-alt p-3">
      <p className="m-0 text-[12px] font-semibold text-text-muted">{label}</p>
      <strong className="mt-1 block text-[17px] text-text">{formatManwonAmount(value)}</strong>
    </div>
  );
}

export type ScoreRanks = Record<ScoreLayerKey, Record<string, number>>;

export function buildScoreRanks(adongs: AdongScore[]): ScoreRanks {
  const rankBy = (pick: (d: AdongScore) => number | null | undefined) => {
    const safeScore = (d: AdongScore) => Number.isFinite(pick(d)) ? Number(pick(d)) : -Infinity;
    const result: Record<string, number> = {};
    adongs
      .filter((d) => Number.isFinite(pick(d)))
      .sort((a, b) => safeScore(b) - safeScore(a))
      .forEach((d, index) => {
        result[d.code] = index + 1;
      });
    return result;
  };
  return {
    composite: rankBy((d) => d.score),
    rent: rankBy((d) => d.score_rent),
    transit: rankBy((d) => d.score_transit),
    amenity: rankBy((d) => d.score_amenity),
    safety: rankBy((d) => d.score_safety),
  };
}

export default MapPopup;
