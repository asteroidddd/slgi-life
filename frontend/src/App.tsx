// Top-level router. Screens registered here per SPEC section 8.
//   /                       → MainMap (4단계)
//   /dashboard              → Dashboard (Phase 0 shell)
//   /login                  → Login (9단계, username/password)
//   /register               → Register (9단계)
//   /mypage                 → MyPage (9단계, SPEC 6.6)
//   /onboarding             → preference modal (7단계)
//
import { lazy, Suspense, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Navigate, Route, Routes } from 'react-router-dom';

import { PageTitleProvider } from './contexts/PageTitleContext';
import { ADONG_GEOJSON_QUERY_KEY, fetchAdongGeoJson } from './hooks/useAdongGeoJson';
import { SEOUL_MASK_GEOJSON_QUERY_KEY, fetchSeoulMaskGeoJson } from './hooks/useSeoulMaskGeoJson';
import DesignSystem from './routes/DesignSystem';
import Login from './routes/Login';
import MainMap from './routes/MainMap';
import MyPage from './routes/MyPage';
import NotFound from './routes/NotFound';
import Register from './routes/Register';

const Dashboard = lazy(() => import('./routes/Dashboard'));

function AppContent() {
  const queryClient = useQueryClient();

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
    <div>
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
        <Route path="/adong/:slug" element={<Navigate to="/" replace />} />
        <Route path="/adong/:slug/explore" element={<Navigate to="/" replace />} />
        <Route path="/compare" element={<Navigate to="/" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/mypage" element={<MyPage />} />
        <Route path="/design-system" element={<DesignSystem />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <PageTitleProvider>
      <AppContent />
    </PageTitleProvider>
  );
}
