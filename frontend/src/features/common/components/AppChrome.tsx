import { lazy, Suspense, useEffect, useState, type ReactNode } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import ThemeToggle from '@/features/common/components/ThemeToggle';
import Tooltip from '@/features/common/components/ui/Tooltip';
import { useAuth } from '@/features/common/contexts/AuthContext';
import { LoginPanel } from '@/features/common/routes/Login';
import { MyPagePanel } from '@/features/common/routes/MyPage';

const PRIMARY_PATHS = new Set(['/', '/select', '/map']);
const AiChatPanel = lazy(() => import('@/features/ai-chat/components/AiChatPanel'));
type AuthMode = 'login' | 'mypage';

function fallbackPath(pathname: string) {
  if (pathname.startsWith('/dashboard')) return '/map';
  if (pathname === '/recommend/results') return '/recommend/conditions';
  return '/select';
}

export function BackButton({ fallbackTo, forceFallback = false }: { fallbackTo?: string; forceFallback?: boolean }) {
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
      className="app-floating-button app-back-button fixed left-6 top-6 z-[1600] no-underline"
    >
      뒤로가기
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
  const requestedAuth = searchParams.get('auth');
  const requestedAi = searchParams.get('ai');
  const onMap = location.pathname === '/map';
  const onRecommendation = location.pathname === '/recommend/conditions' || location.pathname === '/recommend/results';
  const onDashboard = location.pathname.startsWith('/dashboard/');
  const onRealEstate = location.pathname.startsWith('/real-estate');
  const onLegal = location.pathname.startsWith('/legal/');
  const showNeutralNavigation = onRealEstate || onLegal;
  const showMapAction = !onMap && (onRecommendation || onDashboard || showNeutralNavigation);
  const showConditionAction = !location.pathname.startsWith('/recommend/conditions') && (onMap || onDashboard || showNeutralNavigation);

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
        </div>
        {showMapAction || showConditionAction ? (
          <div className="flex items-center gap-2">
            {showMapAction ? (
              <Tooltip label="지도 탐색" placement="bottom">
                <button
                  type="button"
                  className="app-action-button app-action-text-button"
                  aria-label="지도 탐색으로 이동"
                  onClick={() => navigate('/map')}
                >
                  지도 탐색
                </button>
              </Tooltip>
            ) : null}
            {showConditionAction ? (
              <Tooltip label="조건 선택" placement="bottom">
                <button
                  type="button"
                  className="app-action-button app-action-text-button"
                  aria-label="조건 선택으로 이동"
                  onClick={() => navigate('/recommend/conditions')}
                >
                  조건 선택
                </button>
              </Tooltip>
            ) : null}
          </div>
        ) : null}
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
