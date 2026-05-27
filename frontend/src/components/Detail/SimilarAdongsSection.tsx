// SimilarAdongsSection — SPEC 6.3 Section 6 (비슷한 동네).
import { useNavigate } from 'react-router-dom';

import type { AdongDetail } from '@/types/api';

interface SimilarAdongsSectionProps {
  similar: AdongDetail['similar_dongs'];
}

export default function SimilarAdongsSection({ similar }: SimilarAdongsSectionProps) {
  const navigate = useNavigate();

  if (similar.length === 0) {
    return null;
  }

  return (
    <section
      className="max-w-[720px] pt-20 border-t border-divider"
      aria-labelledby="similar-heading"
    >
      <p className="mono-label m-0 mb-3 text-text-subtle" aria-hidden="true">
        NEARBY
      </p>
      <header className="flex items-baseline justify-between gap-4 mb-4 flex-wrap">
        <h2 id="similar-heading" className="m-0 text-section-heading leading-[1.15] font-semibold text-text tracking-[-0.36px]">
          비슷한 동네
        </h2>
        <p className="m-0 text-caption text-text-muted tracking-normal">데이터 유사도 기반 추천</p>
      </header>

      <ul className="list-none m-0 p-0">
        {similar.map((d) => (
          <li key={d.slug} className="border-b border-divider last:border-b-0">
            <button
              type="button"
              className="w-full flex items-center justify-between gap-4 py-4 bg-none border-none cursor-pointer text-left text-inherit tracking-normal transition-all duration-[120ms] ease-out hover:bg-surface-alt hover:pl-3 hover:pr-3 hover:-ml-3 hover:-mr-3 focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2"
              onClick={() => navigate(`/adong/${d.slug}`)}
              aria-label={`${d.gu} ${d.name}, 유사도 ${d.similarity_pct}%`}
            >
              <span className="flex flex-col gap-[2px]">
                <span className="text-caption text-text-muted tracking-normal">{d.gu}</span>
                <span className="text-card-heading leading-[1.2] font-semibold text-text tracking-[-0.28px]">{d.name}</span>
              </span>
              <span className="font-mono text-mono-label font-normal tracking-[0.26px] text-text uppercase">
                유사도 <span className="tabular">{d.similarity_pct.toFixed(1)}</span>%
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
