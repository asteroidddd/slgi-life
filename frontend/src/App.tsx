import { lazy, Suspense, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { AppActions, BackButton, LegalFooter, shouldShowBackButton } from '@/features/common/components/AppChrome';
import CandidateDrawer, { shouldShowCandidateDrawer } from '@/features/candidates/components/CandidateDrawer';
import { PageTitleProvider } from '@/features/common/contexts/PageTitleContext';
import { ADONG_GEOJSON_QUERY_KEY, fetchAdongGeoJson } from '@/features/map/hooks/useAdongGeoJson';
import { SEOUL_MASK_GEOJSON_QUERY_KEY, fetchSeoulMaskGeoJson } from '@/features/map/hooks/useSeoulMaskGeoJson';
import DesignSystem from '@/features/common/routes/DesignSystem';
import Login from '@/features/common/routes/Login';
import MyPage from '@/features/common/routes/MyPage';
import NotFound from '@/features/common/routes/NotFound';
import Register from '@/features/common/routes/Register';
import SelectPage from '@/features/common/routes/SelectPage';
import RecommendationConditions from '@/features/recommendation/routes/RecommendationConditions';
import RecommendationResults from '@/features/recommendation/routes/RecommendationResults';
import LegalInfo from '@/features/legal/routes/LegalInfo';
import MainMap from '@/features/map/routes/MainMap';

const Dashboard = lazy(() => import('@/features/dashboard/routes/Dashboard'));
const AiChatPage = lazy(() => import('@/features/ai-chat/routes/AiChatPage'));
const RealEstatePage = lazy(() => import('@/features/real-estate/routes/RealEstatePage'));

function AppContent() {
  const queryClient = useQueryClient();
  const location = useLocation();

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
    <div className="min-h-screen">
      <AppActions />
      {shouldShowBackButton(location.pathname) ? (
        <BackButton
          fallbackTo={location.pathname === '/recommend/results' ? '/recommend/conditions' : undefined}
          forceFallback={location.pathname === '/recommend/results'}
        />
      ) : null}
      {shouldShowCandidateDrawer(location.pathname) ? <CandidateDrawer /> : null}
      <Routes>
        <Route path="/" element={<Navigate to="/select" replace />} />
        <Route path="/select" element={<SelectPage />} />
        <Route path="/map" element={<MainMap />} />
        <Route
          path="/dashboard/:regionType"
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
        <Route
          path="/dashboard/:regionType/:slug"
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
        <Route path="/recommend/conditions" element={<RecommendationConditions />} />
        <Route path="/recommend/results" element={<RecommendationResults />} />
        <Route
          path="/ai-chat"
          element={
            <Suspense fallback={<PageLoading />}>
              <AiChatPage />
            </Suspense>
          }
        />
        <Route
          path="/real-estate"
          element={
            <Suspense fallback={<PageLoading />}>
              <RealEstatePage />
            </Suspense>
          }
        />
        <Route path="/adong/:slug" element={<Navigate to="/map" replace />} />
        <Route path="/adong/:slug/explore" element={<Navigate to="/map" replace />} />
        <Route path="/compare" element={<Navigate to="/map" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/legal/terms" element={<LegalInfo page="terms" />} />
        <Route path="/legal/privacy" element={<LegalInfo page="privacy" />} />
        <Route path="/legal/data-sources" element={<LegalInfo page="data" />} />
        <Route path="/register" element={<Register />} />
        <Route path="/mypage" element={<MyPage />} />
        <Route path="/design-system" element={<DesignSystem />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
      <LegalFooter />
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

function PageLoading() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-primary-soft text-caption text-text-muted">
      로딩 중...
    </main>
  );
}
