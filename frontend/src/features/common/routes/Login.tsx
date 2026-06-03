import { Navigate, useLocation, useSearchParams } from 'react-router-dom';

import { getKakaoLoginUrl } from '@/features/common/lib/api';
import { useAuth } from '@/features/common/contexts/AuthContext';

const ERROR_MESSAGES: Record<string, string> = {
  kakao_cancelled: '카카오 로그인이 취소되었습니다.',
  kakao_failed: '카카오 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.',
  kakao_not_configured: '카카오 로그인 설정이 아직 완료되지 않았습니다.',
  kakao_state_invalid: '로그인 요청이 만료되었습니다. 다시 시도해 주세요.',
  kakao_user_missing: '카카오 계정 정보를 확인하지 못했습니다.',
  inactive_user: '사용할 수 없는 계정입니다.',
};

const AUTH_RETURN_PATH_KEY = 'slgi-auth-return-path';

function cleanReturnPath(path: string) {
  try {
    const url = new URL(path, window.location.origin);
    if (url.origin !== window.location.origin || url.pathname === '/login') return '/select';
    url.searchParams.delete('auth');
    url.searchParams.delete('error');
    url.searchParams.delete('withdrawn');
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return '/select';
  }
}

function rememberAuthReturnPath(path: string) {
  try {
    window.sessionStorage.setItem(AUTH_RETURN_PATH_KEY, cleanReturnPath(path));
  } catch {
    // Auth can still continue without a return path.
  }
}

function consumeAuthReturnPath() {
  try {
    const path = window.sessionStorage.getItem(AUTH_RETURN_PATH_KEY) || '/select';
    window.sessionStorage.removeItem(AUTH_RETURN_PATH_KEY);
    return cleanReturnPath(path);
  } catch {
    return '/select';
  }
}

function withAuthMode(path: string, mode: 'login' | 'mypage') {
  try {
    const url = new URL(path, window.location.origin);
    if (url.origin !== window.location.origin) return `/select?auth=${mode}`;
    url.searchParams.set('auth', mode);
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return `/select?auth=${mode}`;
  }
}

export function LoginPanel({ error = '', withdrawn = false }: { error?: string; withdrawn?: boolean }) {
  const location = useLocation();

  const startKakaoLogin = () => {
    rememberAuthReturnPath(`${location.pathname}${location.search}${location.hash}`);
    window.location.assign(getKakaoLoginUrl());
  };

  return (
    <section className="grid gap-5 p-8 text-text" aria-labelledby="login-title">
      <div className="grid gap-2 pr-10">
        <h1 id="login-title" className="m-0 text-[34px] font-semibold leading-tight tracking-normal">
          로그인
        </h1>
        <p className="m-0 text-[13px] leading-6 text-text-muted">
          카카오 계정으로 시작합니다. 이메일과 기본 정보는 마이페이지에서 관리할 수 있습니다.
        </p>
      </div>

      {withdrawn ? (
        <div className="rounded-sm border border-border bg-surface-alt px-4 py-3 text-caption leading-[1.4] text-text-muted" role="status">
          회원탈퇴가 완료되었습니다.
        </div>
      ) : null}
      {error ? (
        <div className="rounded-sm border border-danger bg-danger-soft px-4 py-3 text-caption leading-[1.4] text-danger" role="alert">
          {ERROR_MESSAGES[error] ?? '로그인에 실패했습니다. 다시 시도해 주세요.'}
        </div>
      ) : null}

      <button
        type="button"
        onClick={startKakaoLogin}
        className="h-14 rounded-sm border border-[#E1CB00] bg-[#FEE500] px-5 text-[17px] font-semibold text-[#191919] transition hover:brightness-95 focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2"
      >
        카카오로 계속하기
      </button>
    </section>
  );
}

export default function Login() {
  const [params] = useSearchParams();
  const { user, isLoading } = useAuth();
  const error = params.get('error') || '';
  const withdrawn = params.get('withdrawn') === '1';

  if (isLoading) {
    return <main className="min-h-screen bg-primary-soft" aria-label="로그인 확인 중" />;
  }

  if (user) {
    return <Navigate to={withAuthMode(consumeAuthReturnPath(), 'mypage')} replace />;
  }

  const next = new URLSearchParams();
  next.set('auth', 'login');
  if (error) next.set('error', error);
  if (withdrawn) next.set('withdrawn', '1');
  return <Navigate to={`/select?${next.toString()}`} replace />;
}
