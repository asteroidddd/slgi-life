// Register (`/register`) — username/password (+ school/year/nickname optional).
import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { Button, Input } from '@/components/ui';
import { useAuth } from '@/contexts/AuthContext';
import { getAuthErrorMessage } from '@/lib/authErrors';

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [school, setSchool] = useState('');
  const [year, setYear] = useState<string>('');
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

    let yearNum: number | null = null;
    if (year.trim()) {
      const parsed = Number(year);
      if (!Number.isFinite(parsed) || parsed < 1 || parsed > 8) {
        setErrorMsg('학년은 1~8 사이의 숫자여야 해요.');
        return;
      }
      yearNum = Math.trunc(parsed);
    }

    setSubmitting(true);
    try {
      await register({
        username: username.trim(),
        password,
        ...(nickname.trim() ? { nickname: nickname.trim() } : {}),
        ...(school.trim() ? { school: school.trim() } : {}),
        ...(yearNum != null ? { year: yearNum } : {}),
      });
      navigate('/mypage', { replace: true });
    } catch (err) {
      setErrorMsg(
        getAuthErrorMessage(err, '회원가입에 실패했어요. 입력값을 다시 확인해주세요.')
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="relative min-h-screen bg-primary-soft text-text flex items-center justify-center p-6" id="main">
      <button type="button" onClick={() => navigate('/')} className="app-floating-button absolute left-5 top-5 h-10 min-h-10">맵으로 가기</button>
      <div className="w-full max-w-[480px] bg-surface border border-border rounded-card p-8 flex flex-col gap-5" role="form" aria-labelledby="register-title">
        <h1 id="register-title" className="text-section-display leading-[1.05] font-semibold tracking-[-0.96px] text-text m-0">회원가입</h1>
        <p className="text-body-base leading-[1.6] text-text-muted tracking-normal m-0">
          아이디와 비밀번호만 입력해도 가입할 수 있어요. 나머지는 마이페이지에서
          나중에 채워도 OK.
        </p>

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
            placeholder="영문/숫자 4자 이상"
            required
          />
          <Input
            label="비밀번호"
            type="password"
            name="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="8자 이상 권장"
            required
          />
          <Input
            label="닉네임 (선택)"
            name="nickname"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="비워두면 아이디로 표시돼요"
          />
          <Input
            label="학교 (선택)"
            name="school"
            value={school}
            onChange={(e) => setSchool(e.target.value)}
            placeholder="예: 동국대학교"
          />
          <Input
            label="학년 (선택)"
            type="number"
            inputMode="numeric"
            min={1}
            max={8}
            name="year"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            placeholder="예: 3"
          />
          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            loading={submitting}
          >
            가입하고 시작하기
          </Button>
        </form>

        <hr className="h-px bg-border m-0 border-none" />

        <div className="flex flex-col items-center gap-2 text-caption text-text-muted tracking-normal">
          <span>이미 계정이 있으신가요?</span>
          <Link to="/login" className="text-link underline underline-offset-2 font-medium py-1 px-2 rounded-sm transition-all duration-[120ms] ease-out hover:bg-primary-soft focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2">
            로그인하기 →
          </Link>
        </div>
      </div>
    </main>
  );
}
