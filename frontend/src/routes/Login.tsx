import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';

import { getKakaoLoginUrl } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

const ERROR_MESSAGES: Record<string, string> = {
  kakao_cancelled: '카카오 로그인이 취소되었습니다.',
  kakao_failed: '카카오 로그인에 실패했습니다. 잠시 후 다시 시도해주세요.',
  kakao_not_configured: '카카오 로그인 설정이 아직 완료되지 않았습니다.',
  kakao_state_invalid: '로그인 요청이 만료되었습니다. 다시 시도해주세요.',
  kakao_user_missing: '카카오 계정 정보를 확인하지 못했습니다.',
  inactive_user: '사용할 수 없는 계정입니다.',
};

export default function Login() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { user, isLoading } = useAuth();
  const error = params.get('error') || '';
  const withdrawn = params.get('withdrawn') === '1';

  if (!isLoading && user) {
    return <Navigate to="/mypage" replace />;
  }

  return (
    <main className="relative min-h-screen bg-[var(--color-heatmap-1)] text-text flex items-center justify-center p-6" id="main">
      <button
        type="button"
        onClick={() => navigate('/')}
        className="app-floating-button absolute left-5 top-5 h-10 min-h-10"
      >
        맵으로 가기
      </button>
      <section className="w-full max-w-[480px] bg-surface border border-border rounded-card p-8 flex flex-col gap-5 shadow-sm" aria-labelledby="login-title">
        <div className="grid gap-2">
          <h1 id="login-title" className="text-section-display leading-[1.05] font-semibold text-text m-0">로그인</h1>
          <p className="m-0 text-[13px] leading-5 text-text-muted">카카오 계정으로 자취맵을 이용합니다. 이메일은 로그인 후 마이페이지에서 직접 입력합니다.</p>
        </div>

        {withdrawn ? (
          <div className="rounded-sm border border-border bg-surface-alt px-4 py-3 text-caption leading-[1.4] text-text-muted" role="status">
            회원탈퇴가 완료되었습니다.
          </div>
        ) : null}
        {error ? (
          <div className="bg-danger-soft text-danger border border-danger rounded-sm py-3 px-4 text-caption leading-[1.4]" role="alert">
            {ERROR_MESSAGES[error] ?? '로그인에 실패했습니다. 다시 시도해주세요.'}
          </div>
        ) : null}

        <button
          type="button"
          onClick={() => window.location.assign(getKakaoLoginUrl())}
          className="h-12 rounded-sm border border-[#E1CB00] bg-[#FEE500] px-4 text-[15px] font-semibold text-[#191919] transition hover:brightness-95 focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2"
        >
          카카오로 계속하기
        </button>
      </section>
    </main>
  );
}
