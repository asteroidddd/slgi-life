import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import DashboardMiniMap from '@/components/Dashboard/DashboardMiniMap';
import DashboardSections from '@/components/Dashboard/DashboardSections';
import { useAuth } from '@/contexts/AuthContext';
import { useAdongScores, useLdongScores } from '@/hooks/useAdongs';
import { getDashboardRegionAtPoint, getDashboardRegionIntro } from '@/lib/api';
import { dashboardLayoutVars } from '@/lib/dashboardTransition';
import { DEFAULT_WEIGHTS } from '@/types/api';
import type { AdongScore } from '@/types/api';

type RegionLevel = 'adong' | 'ldong';

const SCORE_ITEMS: Array<{
  key: keyof Pick<AdongScore, 'score' | 'score_rent' | 'score_transit' | 'score_amenity' | 'score_safety'>;
  label: string;
}> = [
  { key: 'score', label: '종합' },
  { key: 'score_rent', label: '부동산' },
  { key: 'score_transit', label: '교통' },
  { key: 'score_amenity', label: '편의시설' },
  { key: 'score_safety', label: '안전' },
];

function formatScore(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '-';
  return Math.round(value).toString();
}

function fallbackIntro(region: AdongScore | null) {
  if (!region) return '지역 소개 데이터를 불러오는 중입니다.';
  return `${region.gu} ${region.name}의 주거 점수와 생활 여건을 한눈에 확인할 수 있습니다.`;
}

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [closing, setClosing] = useState(false);
  const [regionSearch, setRegionSearch] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
  const miniMapFrameRef = useRef<HTMLDivElement>(null);

  const explicitRegionType = searchParams.get('region_type');
  const regionLevel: RegionLevel = explicitRegionType === 'adong' || (!explicitRegionType && searchParams.has('adong'))
    ? 'adong'
    : 'ldong';
  const adongScoresQuery = useAdongScores(DEFAULT_WEIGHTS);
  const ldongScoresQuery = useLdongScores(DEFAULT_WEIGHTS);
  const regions = regionLevel === 'ldong' ? (ldongScoresQuery.data ?? []) : (adongScoresQuery.data ?? []);
  const selectedSlug = searchParams.get('slug')
    ?? searchParams.get(regionLevel)
    ?? (regionLevel === 'adong' ? searchParams.get('adong') : searchParams.get('ldong'))
    ?? regions[0]?.slug
    ?? null;

  const selectedRegion = useMemo(
    () => regions.find((region) => region.slug === selectedSlug) ?? regions[0] ?? null,
    [regions, selectedSlug],
  );
  const effectiveSlug = selectedRegion?.slug ?? selectedSlug;
  const regionSearchOptions = useMemo(() => {
    const q = regionSearch.trim().toLowerCase();
    const items = q
      ? regions.filter((region) => {
        const label = `${region.gu} ${region.name}`.toLowerCase();
        return label.includes(q) || region.name.toLowerCase().includes(q);
      })
      : regions;
    return items.slice(0, 24);
  }, [regionSearch, regions]);
  const showRegionSearchResults = searchFocused && regionSearchOptions.length > 0;

  const introQuery = useQuery({
    queryKey: ['dashboard', 'regions', regionLevel, effectiveSlug, 'intro'],
    queryFn: () => getDashboardRegionIntro(regionLevel, effectiveSlug!),
    enabled: !!effectiveSlug,
    staleTime: 300_000,
  });

  const handleRegionChange = useCallback(
    (slug: string) => {
      const next = new URLSearchParams(searchParams);
      next.set('region_type', regionLevel);
      next.set('slug', slug);
      next.delete('adong');
      next.delete('ldong');
      setSearchParams(next, { replace: true });
    },
    [regionLevel, searchParams, setSearchParams],
  );

  const handleRegionLevelChange = useCallback(
    async (nextLevel: RegionLevel) => {
      if (nextLevel === regionLevel) return;
      const nextRegions = nextLevel === 'ldong' ? (ldongScoresQuery.data ?? []) : (adongScoresQuery.data ?? []);
      let nextSlug = nextRegions[0]?.slug ?? '';
      if (selectedRegion && Number.isFinite(selectedRegion.lat) && Number.isFinite(selectedRegion.lng)) {
        try {
          const matched = await getDashboardRegionAtPoint(nextLevel, selectedRegion.lat, selectedRegion.lng);
          nextSlug = matched.slug || nextSlug;
        } catch {
          nextSlug = nextRegions[0]?.slug ?? '';
        }
      }
      const next = new URLSearchParams(searchParams);
      next.set('region_type', nextLevel);
      next.set('slug', nextSlug);
      next.delete('adong');
      next.delete('ldong');
      setRegionSearch('');
      setSearchParams(next, { replace: true });
    },
    [adongScoresQuery.data, ldongScoresQuery.data, regionLevel, searchParams, selectedRegion, setSearchParams],
  );

  const handleRegionSearchSubmit = useCallback(() => {
    const q = regionSearch.trim().toLowerCase();
    if (!q) return;
    const match = regions.find((region) => {
      const label = `${region.gu} ${region.name}`.toLowerCase();
      return label === q || region.name.toLowerCase() === q || region.slug.toLowerCase() === q;
    }) ?? regionSearchOptions[0];
    if (!match) return;
    handleRegionChange(match.slug);
    setRegionSearch(`${match.gu} ${match.name}`);
    setSearchFocused(false);
  }, [handleRegionChange, regionSearch, regionSearchOptions, regions]);

  const handleDashboardClose = useCallback(() => {
    const rect = miniMapFrameRef.current?.getBoundingClientRect();
    if (rect) {
      document.documentElement.style.setProperty('--map-transition-left', `${rect.left}px`);
      document.documentElement.style.setProperty('--map-transition-top', `${rect.top}px`);
      document.documentElement.style.setProperty('--map-transition-width', `${rect.width}px`);
      document.documentElement.style.setProperty('--map-transition-height', `${rect.height}px`);
    }
    setClosing(true);
    window.setTimeout(() => navigate('/?mode=plain'), 360);
  }, [navigate]);

  useEffect(() => {
    if (!regions.length) return;
    const hasSelectedRegion = selectedSlug != null && regions.some((region) => region.slug === selectedSlug);
    if (searchParams.get('region_type') === regionLevel && hasSelectedRegion && searchParams.get('slug')) return;

    const next = new URLSearchParams(searchParams);
    next.set('region_type', regionLevel);
    next.set('slug', hasSelectedRegion ? selectedSlug! : regions[0].slug);
    next.delete('adong');
    next.delete('ldong');
    setSearchParams(next, { replace: true });
  }, [regionLevel, regions, searchParams, selectedSlug, setSearchParams]);

  return (
    <main id="main" className="relative h-screen overflow-hidden bg-primary-soft" style={dashboardLayoutVars()}>
      <div className="fixed bottom-6 left-6 z-[1200] grid gap-2">
        <button
          type="button"
          onClick={handleDashboardClose}
          className="app-floating-button"
        >
          대시보드 닫기
        </button>
      </div>

      <Link
        to={user ? '/mypage' : '/login'}
        className="app-floating-button fixed right-6 top-6 z-[1200]"
      >
        {user ? '마이페이지' : '로그인'}
      </Link>

      {closing ? (
        <div className="map-route-transition map-route-transition--in" aria-hidden="true">
          <div className="map-route-transition__frame" />
        </div>
      ) : null}

      <div className="h-full overflow-y-auto">
        <div className="mx-auto max-w-[var(--dashboard-max-width)] px-[var(--dashboard-page-padding)] py-[var(--dashboard-page-padding)]">
            <div className="mb-3 flex min-h-10 items-center justify-between gap-4">
              <div className="relative w-[430px] max-w-full">
                <label className="flex h-11 w-full items-center gap-3 rounded-card border border-border bg-white/95 px-3 shadow-lg backdrop-blur" aria-label={`${regionLevel === 'adong' ? '행정동' : '법정동'} 검색`}>
                  <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center text-[18px] font-semibold text-text-muted" aria-hidden="true">⌕</span>
                  <input
                    value={regionSearch}
                    onFocus={() => setSearchFocused(true)}
                    onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)}
                    onChange={(event) => {
                      setRegionSearch(event.target.value);
                      setSearchFocused(true);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Escape') {
                        setSearchFocused(false);
                        return;
                      }
                      if (event.key !== 'Enter') return;
                      event.preventDefault();
                      handleRegionSearchSubmit();
                    }}
                    placeholder={`${regionLevel === 'adong' ? '행정동' : '법정동'} 검색`}
                    className="min-w-0 flex-1 border-0 bg-transparent text-[14px] outline-none placeholder:text-text-subtle"
                  />
                </label>
                {showRegionSearchResults ? (
                  <div className="absolute left-0 top-[calc(100%+6px)] z-[900] max-h-[320px] w-[430px] overflow-y-auto overflow-x-hidden rounded-card border border-border bg-white/95 shadow-xl backdrop-blur">
                    {regionSearchOptions.map((region) => (
                      <button
                        key={region.slug}
                        type="button"
                        onMouseDown={(event) => {
                          event.preventDefault();
                          handleRegionChange(region.slug);
                          setRegionSearch(`${region.gu} ${region.name}`);
                          setSearchFocused(false);
                        }}
                        className="block w-full border-t border-border/70 px-3 py-2 text-left transition first:border-t-0 hover:bg-[var(--color-heatmap-1)]"
                      >
                        <span className="block text-[13px] font-semibold text-text">{region.name}</span>
                        <span className="mt-0.5 block truncate text-[12px] text-text-muted">{region.gu} · {regionLevel === 'adong' ? '행정동' : '법정동'}</span>
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="grid grid-cols-2 rounded-[var(--map-control-radius)] border border-border bg-surface-alt p-1" role="group" aria-label="지역 단위">
                <button
                  type="button"
                  onClick={() => handleRegionLevelChange('adong')}
                  className={`h-8 rounded-[var(--map-control-radius)] px-4 text-[13px] font-semibold transition ${
                    regionLevel === 'adong' ? 'bg-white text-text shadow-sm' : 'text-text-muted hover:bg-white/70 hover:text-text'
                  }`}
                >
                  행정동
                </button>
                <button
                  type="button"
                  onClick={() => handleRegionLevelChange('ldong')}
                  className={`h-8 rounded-[var(--map-control-radius)] px-4 text-[13px] font-semibold transition ${
                    regionLevel === 'ldong' ? 'bg-white text-text shadow-sm' : 'text-text-muted hover:bg-white/70 hover:text-text'
                  }`}
                >
                  법정동
                </button>
              </div>
            </div>

          <section className="rounded-card border border-border bg-white p-5 shadow-sm">
            <div className="grid min-h-[var(--dashboard-mini-map-height)] grid-cols-2 gap-[var(--dashboard-grid-gap)]">
              <div className="flex min-w-0 flex-col px-2 pb-1">
                <div>
                  <p className="m-0 text-[15px] font-bold text-text-muted">{selectedRegion?.gu ?? '-'}</p>
                  <h1 className="m-0 mt-1 text-[36px] font-bold tracking-normal text-text">{selectedRegion?.name ?? '지역 선택'}</h1>
                  <p className="m-0 mt-4 max-w-none text-[16px] leading-7 text-text-muted">
                    {introQuery.data?.intro || fallbackIntro(selectedRegion)}
                  </p>
                </div>

                <div className="mt-auto grid grid-cols-5 gap-2 px-1 pt-5">
                  {SCORE_ITEMS.map((item) => (
                    <div key={item.key} className="min-h-[78px] rounded-card border border-border bg-surface-alt px-4 py-3">
                      <p className="m-0 text-[12px] font-bold text-text-muted">{item.label}</p>
                      <strong className="mt-2 block text-[24px] leading-none text-text">
                        {formatScore(selectedRegion?.[item.key])}
                      </strong>
                    </div>
                  ))}
                </div>
              </div>

              <div ref={miniMapFrameRef} className="min-h-[var(--dashboard-mini-map-height)]">
                <DashboardMiniMap
                  regions={regions}
                  regionLevel={regionLevel}
                  selectedSlug={effectiveSlug ?? null}
                  onRegionSelect={handleRegionChange}
                />
              </div>
            </div>
          </section>
          <DashboardSections
            region={selectedRegion}
            regionLevel={regionLevel}
            slug={effectiveSlug ?? null}
          />
        </div>
      </div>
    </main>
  );
}
