// DashboardHeader — adong selector + selected adong display + summary text.

import AdongSelector from './AdongSelector';

export interface DashboardHeaderProps {
  selectedAdong: { slug: string; name: string; gu: string } | null;
  onAdongChange: (slug: string) => void;
  /** One-line summary from AdongSummary (e.g. "월세 평균 72만원, 역세권, 생활시설 충분"). */
  summaryText?: string;
}

export default function DashboardHeader({
  selectedAdong,
  onAdongChange,
  summaryText,
}: DashboardHeaderProps) {
  return (
    <div className="flex items-center justify-between gap-6">
      {/* Left: adong selector */}
      <AdongSelector
        value={selectedAdong?.slug ?? null}
        onChange={onAdongChange}
        className="w-[280px]"
      />

      {/* Right: selected adong display */}
      <div className="flex items-center gap-3 min-w-0">
        {selectedAdong ? (
          <div className="flex items-baseline gap-2 min-w-0">
            <h1 className="text-feature-heading font-semibold text-text whitespace-nowrap">
              {selectedAdong.gu} {selectedAdong.name}
            </h1>
            {summaryText ? (
              <span className="text-caption text-text font-medium truncate max-w-[400px]">
                {summaryText}
              </span>
            ) : (
              <span className="text-caption text-text whitespace-nowrap">
                데이터 불러오는 중...
              </span>
            )}
          </div>
        ) : (
          <span className="text-caption text-text-muted">
            동네를 선택하세요
          </span>
        )}
      </div>
    </div>
  );
}
