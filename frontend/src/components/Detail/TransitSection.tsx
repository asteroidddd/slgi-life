// TransitSection — SPEC 6.3 Section 4 (교통).
import { Badge } from '@/components/ui';
import type { AdongDetail } from '@/types/api';

interface TransitSectionProps {
  transit: AdongDetail['transit'];
}

export default function TransitSection({ transit }: TransitSectionProps) {
  const stations = [...transit.nearest_stations].sort((a, b) => a.rank - b.rank);

  return (
    <section
      className="max-w-[720px] pt-20 border-t border-divider"
      aria-labelledby="transit-heading"
    >
      <p className="mono-label m-0 mb-3 text-text-subtle" aria-hidden="true">
        TRANSIT
      </p>
      <h2 id="transit-heading" className="m-0 text-section-heading leading-[1.15] font-semibold text-text tracking-[-0.36px]">
        교통
      </h2>

      <div className="grid grid-cols-[2fr_1fr] gap-6 items-start mt-5">
        <div className="flex flex-col gap-3" aria-label="가까운 지하철역 3곳">
          <h3 className="m-0 text-feature-heading leading-[1.3] font-semibold text-text">가까운 지하철역</h3>
          <ol className="list-none m-0 p-0 flex flex-col">
            {stations.map((s) => {
              const isFirst = s.rank === 1;
              const variant: 'success' | 'neutral' = isFirst ? 'success' : 'neutral';
              return (
                <li
                  key={`${s.rank}-${s.name}`}
                  className={`flex items-center gap-4 py-3 border-b border-divider last:border-b-0 ${
                    isFirst
                      ? 'bg-surface-alt rounded-card pl-3 pr-3 border-b-transparent mb-1'
                      : ''
                  }`}
                >
                  <div className="shrink-0">
                    <Badge variant={variant} size="md">
                      {s.rank}위
                    </Badge>
                  </div>
                  <div className="flex flex-col gap-1 min-w-0">
                    <div className="text-body-base leading-[1.6] font-medium text-text tracking-normal">
                      {s.name}
                      <span className="font-normal text-text-muted"> · {s.line}</span>
                    </div>
                    <div className="text-caption text-text-muted tracking-normal">
                      도보 <span className="tabular">{s.walking_min}</span>분
                      <span className="text-text-subtle"> · </span>
                      <span className="tabular">{s.walking_distance_m.toLocaleString()}</span>m
                    </div>
                  </div>
                </li>
              );
            })}
            {stations.length === 0 && (
              <li className="py-4 text-text-muted text-body-base text-center">근처 지하철역 정보가 없습니다.</li>
            )}
          </ol>
        </div>

        <div className="flex flex-col gap-3" aria-label="버스 정류장">
          <h3 className="m-0 text-feature-heading leading-[1.3] font-semibold text-text">버스</h3>
          <div className="flex items-center gap-5">
            <div className="flex flex-col gap-1">
              <span className="text-data-display leading-[1] font-semibold tracking-[-0.48px] text-text tabular">{transit.bus.stop_count}</span>
              <span className="text-caption text-text-muted tracking-normal">정류장</span>
            </div>
            <div className="w-px self-stretch bg-divider" aria-hidden="true" />
            <div className="flex flex-col gap-1 items-start">
              <span className="text-feature-heading leading-[1.3] font-normal text-text-muted tabular">
                {transit.bus.route_count}
              </span>
              <span className="text-caption text-text-muted tracking-normal">노선</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
