// Login (`/login`) — username + password form.
import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import { Button, Input } from '@/components/ui';
import { useAuth } from '@/contexts/AuthContext';
import { getAuthErrorMessage } from '@/lib/authErrors';

export default function Login() {
  const navigate = useNavigate();
  const { login, user, isLoading } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (submitting) return;

    setErrorMsg(null);

    if (!username.trim() || !password) {
      setErrorMsg('아이디와 비밀번호를 모두 입력해주세요.');
      return;
    }

    setSubmitting(true);
    try {
      await login({ username: username.trim(), password });
      navigate('/mypage', { replace: true });
    } catch (err) {
      setErrorMsg(
        getAuthErrorMessage(err, '로그인에 실패했어요. 잠시 후 다시 시도해주세요.')
      );
    } finally {
      setSubmitting(false);
    }
  };

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
      <div className="w-full max-w-[480px] bg-surface border border-border rounded-card p-8 flex flex-col gap-5 shadow-sm" role="form" aria-labelledby="login-title">
        <h1 id="login-title" className="text-section-display leading-[1.05] font-semibold tracking-[-0.96px] text-text m-0">로그인</h1>
        {errorMsg && (
          <div className="bg-danger-soft text-danger border border-danger rounded-sm py-3 px-4 text-caption tracking-normal leading-[1.4]" role="alert">
            {errorMsg}
          </div>
        )}

        <form className="flex flex-col gap-4" onSubmit={handleSubmit} noValidate>
          <Input
            label="아이디"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="예: user1234"
            required
          />
          <Input
            label="비밀번호"
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="비밀번호"
            required
          />
          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            loading={submitting}
          >
            로그인
          </Button>
        </form>

        <hr className="h-px bg-border m-0 border-none" />

        <div className="flex flex-col items-center gap-2 text-caption text-text-muted tracking-normal">
          <span>처음 오셨나요?</span>
          <Link to="/register" className="text-link underline underline-offset-2 font-medium py-1 px-2 rounded-sm transition-all duration-[120ms] ease-out hover:bg-primary-soft focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2">
            회원가입은 여기로 →
          </Link>
        </div>
      </div>
    </main>
  );
}
