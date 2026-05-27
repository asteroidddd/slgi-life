// AdongDetail — full detail page (SPEC 6.3).
// Six sections: Hero, RealEstate, Amenity, Transit, Review, SimilarAdongs.
//
// D-3 (design-polish-v2.md): the page-local action group lives in the hero
// right column (visible on first fold). After the hero leaves the viewport,
// a scroll-sticky pill rail slides in from bottom-right with the same 3
// actions in compact form. The previous sticky bottom CTA bar is gone —
// audit feedback flagged it as a non-map FAB pattern.
import { useCallback, useMemo, useRef } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import AmenitySection from '@/components/Detail/AmenitySection';
import HeroSection from '@/components/Detail/HeroSection';
import RealEstateSection from '@/components/Detail/RealEstateSection';
import SimilarAdongsSection from '@/components/Detail/SimilarAdongsSection';
import TransitSection from '@/components/Detail/TransitSection';
import { Button } from '@/components/ui';
import { usePageTitle } from '@/contexts/PageTitleContext';
import { useAdongDetail, useAdongScores } from '@/hooks/useAdongs';
import { useIntersection } from '@/hooks/useIntersection';
import { DEFAULT_WEIGHTS } from '@/types/api';

export default function AdongDetail() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const weights = DEFAULT_WEIGHTS;
  const { data, isLoading, isError, error } = useAdongDetail(slug, weights);

  const scoresQ = useAdongScores(weights);
  const breakdown = useMemo(() => {
    if (!data?.slug || !scoresQ.data) return undefined;
    const row = scoresQ.data.find((d) => d.slug === data.slug);
    if (!row) return undefined;
    return {
      score_rent: row.score_rent,
      score_amenity: row.score_amenity,
      score_transit: row.score_transit,
    };
  }, [data?.slug, scoresQ.data]);

  usePageTitle(data?.name);

  const heroRef = useRef<HTMLDivElement>(null);
  const heroVisible = useIntersection(heroRef, { threshold: 0 });

  const handleAddCompare = useCallback(
    () => alert('비교 목록에 추가됨 (8단계에서 구현)'),
    [],
  );
  const handleFavorite = useCallback(
    () => alert('로그인 후 찜하기 (9단계에서 구현)'),
    [],
  );
  const handleShare = useCallback(
    () => alert('URL 복사 공유 (8단계에서 구현)'),
    [],
  );

  return (
    <div className="min-h-screen bg-bg text-text">
      {isLoading && (
        <div className="max-w-[1200px] mx-auto py-8 px-6 text-center text-body-base text-text-muted tracking-normal" role="status">
          동네 상세 정보를 불러오는 중…
        </div>
      )}

      {isError && (
        <div className="max-w-[1200px] mx-auto py-8 px-6 text-center text-danger flex flex-col items-center gap-3" role="alert">
          정보를 불러오지 못했습니다.
          <span className="text-caption text-text-muted">
            {error instanceof Error ? error.message : '알 수 없는 오류'}
          </span>
          <div className="mt-2">
            <Button
              variant="secondary"
              size="md"
              onClick={() => navigate('/')}
            >
              지도로 돌아가기
            </Button>
          </div>
        </div>
      )}

      <main
        className="max-w-[1200px] mx-auto px-6"
        id="main"
        hidden={!data}
        aria-hidden={!data}
      >
        <div ref={heroRef}>
          {data && (
            <HeroSection
              detail={data}
              breakdown={breakdown}
              onAddCompare={handleAddCompare}
              onFavorite={handleFavorite}
              onShare={handleShare}
            />
          )}
        </div>
        {data && (
          <>
            <RealEstateSection realEstate={data.real_estate} />
            <div className="flex flex-col gap-1 py-5 border-t border-divider border-b border-b-divider my-4">
              <Link
                to={`/adong/${data.slug}/explore`}
                className="text-body-large font-semibold text-text no-underline self-start py-2 hover:text-link"
              >
                자취 시세 더 깊게 탐색하기 →
              </Link>
              <p className="mono-label m-0 text-text-muted">
                필터(유형·기간·보증금·월세·면적)로 시세 분포 자세히 보기
              </p>
            </div>
            <AmenitySection
              amenities={data.amenities}
              allAdongs={scoresQ.data}
              currentSlug={data.slug}
            />
            <TransitSection transit={data.transit} />
            <SimilarAdongsSection similar={data.similar_dongs} />
          </>
        )}

        {data && (
          <div
            className={`fixed right-6 bottom-6 flex gap-2 py-2 px-3 bg-surface border border-border rounded-md z-50 transition-all duration-200 ease-out ${
              heroVisible
                ? 'opacity-0 translate-y-2 pointer-events-none'
                : 'opacity-100 translate-y-0 pointer-events-auto'
            }`}
            aria-label="동네 액션"
            aria-hidden={heroVisible}
            // @ts-expect-error — `inert` lands as a boolean attr but React typed it later.
            inert={heroVisible ? '' : undefined}
          >
            <Button variant="secondary" size="sm" onClick={handleAddCompare}>
              비교에 추가
            </Button>
            <Button variant="secondary" size="sm" onClick={handleFavorite}>
              찜
            </Button>
            <Button variant="secondary" size="sm" onClick={handleShare}>
              공유
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
