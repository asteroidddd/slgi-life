import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import ThemeToggle from '@/features/common/components/ThemeToggle';
import Tooltip from '@/features/common/components/ui/Tooltip';
import { useAuth } from '@/features/common/contexts/AuthContext';
import { LoginPanel } from '@/features/common/routes/Login';
import { MyPagePanel } from '@/features/common/routes/MyPage';
import {
  MAP_RETURN_STORAGE_KEY,
  applyDashboardMapTransitionRect,
  buildDashboardMapUrl,
  readDashboardMapOpenPayload,
  writeDashboardMapOpenPayload,
} from '@/features/map/lib/dashboardMapNavigation';

const PRIMARY_PATHS = new Set(['/', '/recommend/conditions', '/map']);
const AiChatPanel = lazy(() => import('@/features/ai-chat/components/AiChatPanel'));
type AuthMode = 'login' | 'mypage';

function fallbackPath(pathname: string) {
  if (pathname.startsWith('/dashboard')) return '/map';
  if (pathname === '/recommend/results') return '/recommend/conditions';
  return '/recommend/conditions';
}

export function BackButton({
  fallbackTo,
  forceFallback = false,
  label = '뒤로가기',
}: {
  fallbackTo?: string;
  forceFallback?: boolean;
  label?: string;
}) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <button
      type="button"
      onClick={() => {
        if (forceFallback && fallbackTo) {
          navigate(fallbackTo);
          return;
        }
        if (location.key !== 'default') {
          navigate(-1);
          return;
        }
        navigate(fallbackTo ?? fallbackPath(location.pathname));
      }}
      className="app-floating-button app-flow-button app-back-button fixed left-6 top-6 z-[1600] no-underline"
    >
      {label}
    </button>
  );
}

export function AppActions() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, isLoading } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>('login');
  const [aiOpen, setAiOpen] = useState(false);
  const [aiMounted, setAiMounted] = useState(false);
  const [aiCompareCandidates, setAiCompareCandidates] = useState(false);
  const [loginNotice, setLoginNotice] = useState({ error: '', withdrawn: false });
  const [mapTransitioning, setMapTransitioning] = useState(false);
  const mapTransitionTimerRef = useRef<number | null>(null);
  const requestedAuth = searchParams.get('auth');
  const requestedAi = searchParams.get('ai');
  const onMap = location.pathname === '/map';

  useEffect(() => () => {
    if (mapTransitionTimerRef.current != null) window.clearTimeout(mapTransitionTimerRef.current);
  }, []);

  useEffect(() => {
    setAuthOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (isLoading || !user || user.email?.trim()) return;
    setAuthMode('mypage');
    setLoginNotice({ error: '', withdrawn: false });
    setAuthOpen(true);
  }, [isLoading, user]);

  useEffect(() => {
    if (requestedAuth !== 'login' && requestedAuth !== 'mypage') return;
    setAuthMode(requestedAuth);
    setLoginNotice({
      error: searchParams.get('error') ?? '',
      withdrawn: searchParams.get('withdrawn') === '1',
    });
    setAuthOpen(true);
    const next = new URLSearchParams(searchParams);
    next.delete('auth');
    next.delete('error');
    next.delete('withdrawn');
    setSearchParams(next, { replace: true });
  }, [requestedAuth, searchParams, setSearchParams]);

  useEffect(() => {
    if (requestedAi !== '1') return;
    const context = searchParams.get('context') ?? searchParams.get('ai_context');
    setAiCompareCandidates(context === 'candidates');
    setAiMounted(true);
    setAiOpen(true);
    const next = new URLSearchParams(searchParams);
    next.delete('ai');
    next.delete('context');
    next.delete('ai_context');
    setSearchParams(next, { replace: true });
  }, [requestedAi, searchParams, setSearchParams]);

  const openAccountDialog = () => {
    setAuthMode(user ? 'mypage' : 'login');
    setLoginNotice({ error: '', withdrawn: false });
    setAuthOpen(true);
  };

  const openAiPanel = () => {
    setAiCompareCandidates(false);
    setAiMounted(true);
    setAiOpen(true);
  };

  const toggleMapView = () => {
    if (onMap) {
      let returnTo = '';
      try {
        returnTo = window.sessionStorage.getItem(MAP_RETURN_STORAGE_KEY) ?? '';
      } catch {
        returnTo = '';
      }
      const safeReturnTo = returnTo.startsWith('/') && !returnTo.startsWith('/map')
        ? returnTo
        : '/recommend/conditions';
      navigate(safeReturnTo);
      return;
    }

    const returnTo = `${location.pathname}${location.search}${location.hash}`;
    try {
      window.sessionStorage.setItem(MAP_RETURN_STORAGE_KEY, returnTo);
    } catch {
      // If sessionStorage is blocked, the map button still opens the map.
    }

    if (location.pathname.startsWith('/dashboard')) {
      const payload = readDashboardMapOpenPayload();
      if (payload?.view) {
        const nextPayload = {
          ...payload,
          returnTo,
          updatedAt: Date.now(),
        };
        writeDashboardMapOpenPayload(nextPayload);
        applyDashboardMapTransitionRect(nextPayload.rect);
        setMapTransitioning(true);
        if (mapTransitionTimerRef.current != null) window.clearTimeout(mapTransitionTimerRef.current);
        mapTransitionTimerRef.current = window.setTimeout(() => {
          mapTransitionTimerRef.current = null;
          setMapTransitioning(false);
          navigate(buildDashboardMapUrl(nextPayload), {
            state: { dashboardMapView: nextPayload.view },
          });
        }, 360);
        return;
      }
    }

    navigate('/map');
  };

  return (
    <>
      <nav className="app-actions fixed right-6 top-6 z-[1600] flex flex-col items-end gap-2" aria-label="주요 동작">
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Tooltip label={user ? '마이페이지' : '로그인'} placement="bottom">
            <button
              type="button"
              className="app-action-button app-account-button"
              aria-label={user ? '마이페이지 열기' : '로그인 열기'}
              onClick={openAccountDialog}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="8" r="4" />
                <path d="M4.5 20c1.7-4 4.3-6 7.5-6s5.8 2 7.5 6" />
              </svg>
            </button>
          </Tooltip>
          <Tooltip label="AI 채팅" placement="bottom">
            <button
              type="button"
              className="app-action-button app-ai-button"
              aria-label="AI 채팅 열기"
              aria-pressed={aiOpen}
              onClick={openAiPanel}
            >
              AI
            </button>
          </Tooltip>
          <Tooltip label={onMap ? '지도 닫기' : '지도에서 보기'} placement="bottom">
            <button
              type="button"
              className="app-action-button app-map-button"
              aria-label={onMap ? '지도 닫기' : '지도에서 보기'}
              aria-pressed={onMap}
              onClick={toggleMapView}
            >
              {onMap ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M6 6l12 12" />
                  <path d="M18 6 6 18" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M3 6.5 8 4l6 2.5 5-2.5v13.5l-5 2.5-6-2.5-5 2.5V6.5Z" />
                  <path d="M8 4v13.5" />
                  <path d="M14 6.5V20" />
                </svg>
              )}
            </button>
          </Tooltip>
        </div>
      </nav>

      {authOpen ? (
        <AuthDialog onClose={() => setAuthOpen(false)}>
          {authMode === 'mypage' && (user || isLoading)
            ? <MyPagePanel onClose={() => setAuthOpen(false)} />
            : <LoginPanel error={loginNotice.error} withdrawn={loginNotice.withdrawn} />}
        </AuthDialog>
      ) : null}
      {aiMounted ? (
        <Suspense fallback={null}>
          <AiChatPanel
            key={user?.id ?? 'guest'}
            isOpen={aiOpen}
            compareCandidates={aiCompareCandidates}
            onClose={() => setAiOpen(false)}
          />
        </Suspense>
      ) : null}
      {mapTransitioning ? (
        <div className="map-route-transition map-route-transition--in" aria-hidden="true">
          <div className="map-route-transition__frame" />
        </div>
      ) : null}
    </>
  );
}

function AuthDialog({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[1700] flex items-center justify-center bg-black/35 p-6" role="dialog" aria-modal="true">
      <button type="button" className="absolute inset-0 cursor-default" aria-label="닫기" onClick={onClose} />
      <div className="relative max-h-[calc(100vh-48px)] w-full max-w-[620px] overflow-y-auto rounded-card border border-border bg-surface shadow-xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-10 h-8 w-8 rounded-[8px] bg-surface-alt text-[18px] font-bold text-text-muted transition hover:text-text"
          aria-label="닫기"
        >
          ×
        </button>
        {children}
      </div>
    </div>
  );
}

export function LegalFooter() {
  return (
    <footer className="legal-footer" aria-label="정책 링크">
      <Link to="/legal/terms">이용약관</Link>
      <Link to="/legal/privacy">개인정보처리방침</Link>
      <Link to="/legal/data-sources">데이터출처</Link>
    </footer>
  );
}

export function shouldShowBackButton(pathname: string) {
  if (PRIMARY_PATHS.has(pathname)) return false;
  if (pathname.startsWith('/legal/')) return false;
  return true;
}
