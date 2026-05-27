// Top-level router. Screens registered here per SPEC section 8.
//   /                       → MainMap (4단계)
//   /dashboard              → Dashboard (Phase 0 shell)
//   /adong/:slug             → AdongDetail (6단계)
//   /compare?adongs=A,B,C    → Compare (8단계)
//   /login                  → Login (9단계, username/password)
//   /register               → Register (9단계)
//   /mypage                 → MyPage (9단계, SPEC 6.6)
//   /onboarding             → preference modal (7단계)
//
// Stage 3: <TopNav> renders above every route. <PageTitleProvider> lets
// individual pages publish their title to the contextual TopNav center
// zone (D-2 + R-2 design-polish-v2 plan).
//
// AiPanelProvider wraps AppContent + AiSidePanel so that the main content
// area can shift left when the AI panel opens (margin-right transition).
import { lazy, Suspense, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Route, Routes, useLocation } from 'react-router-dom';

import AiSidePanel from './components/Layout/AiSidePanel';
import TopNav from './components/Layout/TopNav';
import { AiPanelProvider, useAiPanel } from './contexts/AiPanelContext';
import { PageTitleProvider } from './contexts/PageTitleContext';
import { ADONG_GEOJSON_QUERY_KEY, fetchAdongGeoJson } from './hooks/useAdongGeoJson';
import { SEOUL_MASK_GEOJSON_QUERY_KEY, fetchSeoulMaskGeoJson } from './hooks/useSeoulMaskGeoJson';
import Compare from './routes/Compare';
import DesignSystem from './routes/DesignSystem';
import AdongDetail from './routes/AdongDetail';
import AdongExplore from './routes/AdongExplore';
import Login from './routes/Login';
import MainMap from './routes/MainMap';
import MyPage from './routes/MyPage';
import NotFound from './routes/NotFound';
import Register from './routes/Register';

const Dashboard = lazy(() => import('./routes/Dashboard'));

function AppContent() {
  const { isOpen } = useAiPanel();
  const queryClient = useQueryClient();
  const location = useLocation();
  const isChromeLessRoute = location.pathname === '/' || location.pathname === '/dashboard' || location.pathname === '/login' || location.pathname === '/register';

  useEffect(() => {
    queryClient.prefetchQuery({
      queryKey: ADONG_GEOJSON_QUERY_KEY,
      queryFn: fetchAdongGeoJson,
      staleTime: Infinity,
    });
    queryClient.prefetchQuery({
      queryKey: SEOUL_MASK_GEOJSON_QUERY_KEY,
      queryFn: fetchSeoulMaskGeoJson,
      staleTime: Infinity,
    });
  }, [queryClient]);

  return (
    <div
      className={`transition-[margin] duration-300 ease-out ${isOpen && !isChromeLessRoute ? 'mr-[400px]' : ''}`}
    >
      {!isChromeLessRoute ? <TopNav /> : null}
      <Routes>
        <Route path="/" element={<MainMap />} />
        <Route
          path="/dashboard"
          element={
            <Suspense
              fallback={
                <div className="flex items-center justify-center h-[calc(100vh-var(--space-14))]">
                  <span className="text-text-muted text-caption">
                    로딩 중...
                  </span>
                </div>
              }
            >
              <Dashboard />
            </Suspense>
          }
        />
        <Route path="/adong/:slug" element={<AdongDetail />} />
        <Route path="/adong/:slug/explore" element={<AdongExplore />} />
        <Route path="/compare" element={<Compare />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/mypage" element={<MyPage />} />
        <Route path="/design-system" element={<DesignSystem />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </div>
  );
}


function AiPanelHost() {
  const location = useLocation();
  if (location.pathname === '/' || location.pathname === '/dashboard' || location.pathname === '/login' || location.pathname === '/register') return null;
  return <AiSidePanel />;
}

export default function App() {
  return (
    <PageTitleProvider>
      <AiPanelProvider>
        <AppContent />
        <AiPanelHost />
      </AiPanelProvider>
    </PageTitleProvider>
  );
}
