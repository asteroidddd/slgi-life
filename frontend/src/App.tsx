import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { AppActions, BackButton, LegalFooter, shouldShowBackButton } from '@/features/common/components/AppChrome';
import CandidateDrawer, { shouldShowCandidateDrawer } from '@/features/candidates/components/CandidateDrawer';
import { PageTitleProvider } from '@/features/common/contexts/PageTitleContext';
import Login from '@/features/common/routes/Login';
import MyPage from '@/features/common/routes/MyPage';
import NotFound from '@/features/common/routes/NotFound';
import Register from '@/features/common/routes/Register';
import RecommendationConditions from '@/features/recommendation/routes/RecommendationConditions';
import RecommendationResults from '@/features/recommendation/routes/RecommendationResults';
import LegalInfo from '@/features/legal/routes/LegalInfo';

const Dashboard = lazy(() => import('@/features/dashboard/routes/Dashboard'));
const AiChatPage = lazy(() => import('@/features/ai-chat/routes/AiChatPage'));
const RealEstatePage = lazy(() => import('@/features/real-estate/routes/RealEstatePage'));
const MainMap = lazy(() => import('@/features/map/routes/MainMap'));

function AppContent() {
  const location = useLocation();

  return (
    <div className="min-h-screen">
      <AppActions />
      {shouldShowBackButton(location.pathname) ? (
        <BackButton
          fallbackTo={location.pathname === '/recommend/results' ? '/recommend/conditions' : undefined}
          forceFallback={location.pathname === '/recommend/results'}
          label={location.pathname === '/recommend/results' ? '조건 재입력' : undefined}
        />
      ) : null}
      {shouldShowCandidateDrawer(location.pathname) ? <CandidateDrawer /> : null}
      <Routes>
        <Route path="/" element={<Navigate to="/recommend/conditions" replace />} />
        <Route path="/select" element={<Navigate to="/recommend/conditions" replace />} />
        <Route
          path="/map"
          element={
            <Suspense fallback={<PageLoading />}>
              <MainMap />
            </Suspense>
          }
        />
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
        <Route path="/login" element={<Login />} />
        <Route path="/legal/terms" element={<LegalInfo page="terms" />} />
        <Route path="/legal/privacy" element={<LegalInfo page="privacy" />} />
        <Route path="/legal/data-sources" element={<LegalInfo page="data" />} />
        <Route path="/register" element={<Register />} />
        <Route path="/mypage" element={<MyPage />} />
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
