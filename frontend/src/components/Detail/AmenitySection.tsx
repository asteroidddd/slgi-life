// AmenitySection — SPEC 6.3 Section 3 (편의시설).
//
// R-3 + A-7a (design-polish-v2.md): each row exposes 4 data cells:
//   name | score (count) | density per ㎢ | TOP X% rank percentile
// The 4th cell is computed on the frontend via lib/percentile.ts using the
// all-adongs /api/adongs/scores response (`useAdongScores` already cached by
// MainMap → React Query usually dedups on this route).
//
// P-11 / D-4: the Badge used to encode the level (충분/보통/부족). Now that
// the row carries a numeric TOP X% cell, the verbal duplicate is removed —
// the score and rank percentile encode the same information without the
// ambiguous "ad-like" label the audit flagged.
import { useMemo } from 'react';

import { computeAmenityPercentile } from '@/lib/percentile';
import type { AdongDetail, AdongScore } from '@/types/api';

interface AmenitySectionProps {
  amenities: AdongDetail['amenities'];
  /** All-adongs score table for the percentile compute. Optional — when
   *  absent (loading or error), the rank cell renders "—". */
  allAdongs?: AdongScore[];
  /** Slug of the adong currently being shown — needed to look up its
   *  score_amenity in the all-adongs table. */
  currentSlug: string;
}

export default function AmenitySection({
  amenities,
  allAdongs,
  currentSlug,
}: AmenitySectionProps) {
  const currentScore = useMemo(() => {
    if (!allAdongs) return undefined;
    return allAdongs.find((d) => d.slug === currentSlug)?.score_amenity;
  }, [allAdongs, currentSlug]);

  return (
    <section
      className="max-w-[720px] pt-20 border-t border-divider"
      aria-labelledby="amenity-heading"
    >
      <p className="mono-label m-0 mb-3 text-text-subtle" aria-hidden="true">
        AMENITIES
      </p>
      <header className="flex items-baseline justify-between gap-4 mb-5 flex-wrap">
        <h2 id="amenity-heading" className="m-0 text-section-heading leading-[1.15] font-semibold text-text tracking-[-0.36px]">
          편의시설
        </h2>
        <p className="m-0 text-caption text-text-muted tracking-normal">
          개수와 ㎢당 밀도, 서울 기준 상위 % (TOP) 함께 표시.
        </p>
      </header>

      <ul className="list-none m-0 p-0">
        {amenities.map((item) => {
          const top =
            currentScore != null
              ? computeAmenityPercentile(allAdongs, item.category, currentScore)
              : null;
          return (
            <li
              key={item.category}
              className="grid grid-cols-[1fr_84px_84px_80px] items-baseline gap-3 py-3 border-b border-divider last:border-b-0"
            >
              <span className="text-feature-heading leading-[1.3] font-semibold text-text tracking-normal">
                {item.category}
              </span>
              <span className="inline-flex items-baseline gap-[2px] justify-end">
                <span className="text-feature-heading leading-[1.3] text-text tabular">{item.count}</span>
                <span className="text-caption text-text-muted tracking-normal">개</span>
              </span>
              <span className="inline-flex items-baseline gap-[2px] justify-end">
                <span className="text-body-base font-normal text-text-muted tabular">
                  {item.density_per_km2.toFixed(1)}
                </span>
                <span className="text-caption text-text-muted tracking-normal">/㎢</span>
              </span>
              <span className="text-right text-text-subtle mono-label">
                {top == null ? '—' : `TOP ${top}%`}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
