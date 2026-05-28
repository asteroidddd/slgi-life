import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import DashboardMiniMap from '@/components/Dashboard/DashboardMiniMap';
import { useAuth } from '@/contexts/AuthContext';
import { useAdongScores } from '@/hooks/useAdongs';
import { dashboardLayoutVars } from '@/lib/dashboardTransition';
import { DEFAULT_WEIGHTS } from '@/types/api';

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [closing, setClosing] = useState(false);
  const miniMapFrameRef = useRef<HTMLDivElement>(null);
  const { data: adongs } = useAdongScores(DEFAULT_WEIGHTS);

  const selectedSlug = searchParams.get('adong') ?? adongs?.[0]?.slug ?? null;

  const handleAdongChange = useCallback(
    (slug: string) => {
      setSearchParams({ adong: slug }, { replace: true });
    },
    [setSearchParams],
  );

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
    if (!searchParams.has('adong') && adongs?.[0]?.slug) {
      setSearchParams({ adong: adongs[0].slug }, { replace: true });
    }
  }, [adongs, searchParams, setSearchParams]);

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
          <div className="grid grid-cols-2 gap-[var(--dashboard-grid-gap)]">
            <div className="min-h-[var(--dashboard-mini-map-height)]" aria-hidden="true" />
            <div ref={miniMapFrameRef} className="min-h-[var(--dashboard-mini-map-height)]">
              <DashboardMiniMap
                adongs={adongs ?? []}
                selectedSlug={selectedSlug}
                onAdongSelect={handleAdongChange}
              />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
