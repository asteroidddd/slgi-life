// TopNav — global 3-zone navigation chrome (R-2 Stage 3).
//
// Center zone: auth pages show nothing; all other pages show nav tabs
// (맵/대시보드) + contextual page title (if any) + AI search button.
import { Link, NavLink, useLocation } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';
import { useAiPanel } from '@/contexts/AiPanelContext';
import { usePageTitleValue } from '@/contexts/PageTitleContext';
import iconSvg from '@/assets/icon.svg';

function dongSlugFromPath(pathname: string): string | undefined {
  const match = pathname.match(/^\/adong\/([^/]+)/);
  return match?.[1];
}

type AuthVariant = 'auth-login' | 'auth-register' | 'default';

/** Contextual title shown after the nav tabs (e.g. "동네 비교", adong name). */
type ContextualTitle =
  | { kind: 'none' }
  | { kind: 'static'; label: string }
  | { kind: 'dongDetail' }
  | { kind: 'mypage' };

interface RouteSpec {
  /** Whether to show nav tabs + AI button (false only for auth pages). */
  showNav: boolean;
  contextualTitle: ContextualTitle;
  authVariant: AuthVariant;
}

function specForPath(pathname: string): RouteSpec {
  if (pathname === '/login')
    return { showNav: false, contextualTitle: { kind: 'none' }, authVariant: 'auth-register' };
  if (pathname === '/register')
    return { showNav: false, contextualTitle: { kind: 'none' }, authVariant: 'auth-login' };
  if (pathname === '/compare')
    return { showNav: true, contextualTitle: { kind: 'static', label: '동네 비교' }, authVariant: 'default' };
  if (pathname === '/mypage')
    return { showNav: true, contextualTitle: { kind: 'mypage' }, authVariant: 'default' };
  if (pathname.startsWith('/adong/'))
    return { showNav: true, contextualTitle: { kind: 'dongDetail' }, authVariant: 'default' };
  return { showNav: true, contextualTitle: { kind: 'none' }, authVariant: 'default' };
}

/** Renders the contextual title text (adong name, page label, etc.). */
function ContextualTitleText({
  spec,
  publishedTitle,
  dongSlug,
  user,
}: {
  spec: RouteSpec;
  publishedTitle: string | undefined;
  dongSlug: string | undefined;
  user: { nickname: string; username: string } | null;
}) {
  const { contextualTitle } = spec;
  let text: string | undefined;

  if (contextualTitle.kind === 'static') text = contextualTitle.label;
  else if (contextualTitle.kind === 'dongDetail') text = publishedTitle ?? dongSlug;
  else if (contextualTitle.kind === 'mypage')
    text = user ? (user.nickname?.trim() || user.username) : undefined;

  if (!text) return null;

  return (
    <>
      <span className="text-text-subtle mx-2" aria-hidden="true">
        &middot;
      </span>
      <span className="text-caption font-normal text-text whitespace-nowrap overflow-hidden text-ellipsis">
        {text}
      </span>
    </>
  );
}

const navLinkBase = 'text-caption px-4 py-1.5 rounded-pill transition-colors duration-200 no-underline';
const navLinkActive = `${navLinkBase} bg-primary-soft text-primary font-medium`;
const navLinkInactive = `${navLinkBase} text-text-muted hover:text-text`;

export default function TopNav() {
  const location = useLocation();
  const { user } = useAuth();
  const { open: openAiPanel } = useAiPanel();
  const publishedTitle = usePageTitleValue();

  const spec = specForPath(location.pathname);
  const dongSlug = dongSlugFromPath(location.pathname);

  return (
    <header className="sticky top-0 z-[1000] w-full h-[var(--space-14)] bg-surface border-b border-divider" role="banner">
      <a
        className="absolute left-3 top-1 px-3 py-1 bg-primary text-surface rounded-sm text-caption no-underline -translate-y-[150%] transition-transform duration-[120ms] ease-out focus-visible:translate-y-0 focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2"
        href="#main"
      >
        메인 콘텐츠로 건너뛰기
      </a>

      <div className="flex items-center justify-between h-full px-6 max-w-[1440px] mx-auto">
        {/* Left zone: logo + nav links */}
        <div className="flex items-center gap-6 min-w-0">
          <Link
            to="/"
            className="inline-flex items-center gap-2 no-underline text-text font-normal tracking-normal hover:text-secondary focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2 focus-visible:rounded-sm shrink-0"
            aria-label="홈으로"
          >
            <img src={iconSvg} alt="" className="w-[var(--control-height-sm)] h-[var(--control-height-sm)] shrink-0 object-contain" aria-hidden="true" />
            <span className="text-body-base font-semibold">자취맵</span>
          </Link>

          {spec.showNav && (
            <>
              <nav className="flex items-center gap-2" aria-label="주요 메뉴">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) => (isActive ? navLinkActive : navLinkInactive)}
                >
                  맵
                </NavLink>
                <NavLink
                  to="/dashboard"
                  className={({ isActive }) => (isActive ? navLinkActive : navLinkInactive)}
                >
                  대시보드
                </NavLink>
              </nav>

              {/* Contextual title (optional) */}
              <ContextualTitleText
                spec={spec}
                publishedTitle={publishedTitle}
                dongSlug={dongSlug}
                user={user}
              />
            </>
          )}
        </div>

        {/* Right zone: AI button + user menu */}
        <div className="flex items-center gap-5">
          {spec.showNav && (
            <button
              onClick={openAiPanel}
              className="inline-flex items-center gap-1.5 rounded-full border border-divider px-4 py-1.5 text-text-muted text-caption hover:border-primary hover:text-primary transition-colors duration-200 cursor-pointer bg-surface"
              aria-label="AI에게 물어보기"
            >
              <span aria-hidden="true" className="text-micro">&#10024;</span>
              <span>AI에게 물어보기</span>
            </button>
          )}
          <nav className="flex items-center gap-3" aria-label="사용자 메뉴">
            {spec.authVariant === 'auth-login' && (
              <Link to="/login" className="inline-flex items-center gap-1 no-underline text-text text-caption tracking-normal py-2 px-3 rounded-sm transition-all duration-[120ms] ease-out hover:bg-primary-soft hover:text-secondary focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2">
                로그인 →
              </Link>
            )}
            {spec.authVariant === 'auth-register' && (
              <Link to="/register" className="inline-flex items-center gap-1 no-underline text-text text-caption tracking-normal py-2 px-3 rounded-sm transition-all duration-[120ms] ease-out hover:bg-primary-soft hover:text-secondary focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2">
                회원가입 →
              </Link>
            )}
            {spec.authVariant === 'default' &&
              (user ? (
                <Link to="/mypage" className="inline-flex items-center gap-1 no-underline text-text text-caption tracking-normal py-2 px-3 rounded-sm transition-all duration-[120ms] ease-out hover:bg-primary-soft hover:text-secondary focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2">
                  <span className="text-text font-medium">
                    {(user.nickname && user.nickname.trim()) || user.username}
                  </span>
                  <span className="text-text-subtle" aria-hidden="true">
                    {' · '}
                  </span>
                  <span>마이페이지</span>
                </Link>
              ) : (
                <Link to="/login" className="inline-flex items-center gap-1 no-underline text-text-muted text-caption tracking-normal py-2 px-3 rounded-sm transition-all duration-[120ms] ease-out hover:bg-primary-soft hover:text-secondary focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2">
                  로그인 →
                </Link>
              ))}
          </nav>
        </div>
      </div>
    </header>
  );
}
