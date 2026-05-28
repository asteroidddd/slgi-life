import { useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import { Button, Input, Select } from '@/components/ui';
import { useAuth } from '@/contexts/AuthContext';
import { getAuthErrorMessage } from '@/lib/authErrors';
import { getUniversityOptions } from '@/lib/api';

export default function Register() {
  const navigate = useNavigate();
  const { register, user, isLoading } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [school, setSchool] = useState('');
  const [address, setAddress] = useState('');
  const [year, setYear] = useState<string>('');
  const [termsAgreed, setTermsAgreed] = useState(false);
  const [openPolicy, setOpenPolicy] = useState<'terms' | 'privacy' | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (submitting) return;
    setErrorMsg(null);

    if (!username.trim() || !password) {
      setErrorMsg('아이디와 비밀번호를 입력해주세요.');
      return;
    }
    if (!termsAgreed) {
      setErrorMsg('이용약관과 개인정보처리방침에 동의해야 가입할 수 있습니다.');
      return;
    }

    let yearNum: number | null = null;
    if (year.trim()) {
      const parsed = Number(year);
      if (!Number.isFinite(parsed) || parsed < 1 || parsed > 8) {
        setErrorMsg('학년은 1부터 8 사이의 숫자로 입력해주세요.');
        return;
      }
      yearNum = Math.trunc(parsed);
    }

    setSubmitting(true);
    try {
      await register({
        username: username.trim(),
        password,
        terms_agreed: true,
        ...(nickname.trim() ? { nickname: nickname.trim() } : {}),
        ...(school.trim() ? { school: school.trim() } : {}),
        ...(address.trim() ? { address: address.trim() } : {}),
        ...(yearNum != null ? { year: yearNum } : {}),
      });
      navigate('/mypage', { replace: true });
    } catch (err) {
      setErrorMsg(getAuthErrorMessage(err, '회원가입에 실패했습니다. 입력값을 다시 확인해주세요.'));
    } finally {
      setSubmitting(false);
    }
  };

  if (!isLoading && user) {
    return <Navigate to="/mypage" replace />;
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center bg-[var(--color-heatmap-1)] p-6 text-text" id="main">
      <button type="button" onClick={() => navigate('/')} className="app-floating-button absolute left-5 top-5 h-10 min-h-10">맵으로 가기</button>
      <div className="flex w-full max-w-[480px] flex-col gap-5 rounded-card border border-border bg-surface p-8 shadow-sm" role="form" aria-labelledby="register-title">
        <h1 id="register-title" className="m-0 text-section-display font-semibold leading-[1.05] text-text">회원가입</h1>

        {errorMsg ? (
          <div className="rounded-sm border border-danger bg-danger-soft px-4 py-3 text-caption leading-[1.4] text-danger" role="alert">
            {errorMsg}
          </div>
        ) : null}

        <form className="flex flex-col gap-4" onSubmit={handleSubmit} noValidate>
          <Input label={<FieldLabel text="아이디" required />} name="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="예: user1234" required />
          <Input label={<FieldLabel text="비밀번호" required />} type="password" name="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="8자 이상 권장" required />
          <Input label={<FieldLabel text="닉네임" />} name="nickname" value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="비워두면 아이디로 표시됩니다" />
          <UniversitySelect value={school} onChange={setSchool} label={<FieldLabel text="다니는 대학" />} />
          <Input label={<FieldLabel text="주소" />} name="address" autoComplete="street-address" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="예: 서울특별시 중구 세종대로 110" />
          <Input label={<FieldLabel text="학년" />} type="number" inputMode="numeric" min={1} max={8} name="year" value={year} onChange={(e) => setYear(e.target.value)} placeholder="예: 3" />

          <label className="flex items-start gap-2 rounded-card border border-border bg-surface-alt px-3 py-2 text-[12px] leading-5 text-text-muted">
            <input
              type="checkbox"
              checked={termsAgreed}
              onChange={(e) => setTermsAgreed(e.target.checked)}
              className="mt-1"
            />
            <span>
              <button type="button" onClick={() => setOpenPolicy('terms')} className="font-semibold text-link underline underline-offset-2">이용약관</button>
              과{' '}
              <button type="button" onClick={() => setOpenPolicy('privacy')} className="font-semibold text-link underline underline-offset-2">개인정보처리방침</button>
              에 동의합니다.
            </span>
          </label>

          <Button type="submit" variant="primary" size="lg" fullWidth loading={submitting}>
            가입하고 시작하기
          </Button>
        </form>

        <hr className="m-0 h-px border-none bg-border" />

        <div className="flex flex-col items-center gap-2 text-caption text-text-muted">
          <span>이미 계정이 있나요?</span>
          <Link to="/login" className="rounded-sm px-2 py-1 font-medium text-link underline underline-offset-2 transition hover:bg-primary-soft">
            로그인하기
          </Link>
        </div>
      </div>
      {openPolicy ? <PolicyPanel panel={openPolicy} onClose={() => setOpenPolicy(null)} /> : null}
    </main>
  );
}

function FieldLabel({ text, required = false }: { text: string; required?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span>{text}</span>
      <span className={required ? 'text-danger' : 'text-text-subtle'}>{required ? '필수' : '선택'}</span>
    </span>
  );
}

function UniversitySelect({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (value: string) => void;
  label: ReactNode;
}) {
  const { data, isLoading } = useQuery({ queryKey: ['universities'], queryFn: getUniversityOptions, staleTime: 60 * 60 * 1000 });
  const schools = data?.schools ?? [];

  return (
    <label className="grid gap-2 text-caption text-text">
      {label}
      <Select value={value} onChange={(e) => onChange(e.target.value)} disabled={isLoading}>
        <option value="">{isLoading ? '대학 목록 불러오는 중' : '대학 미입력'}</option>
        {schools.map((school) => (
          <option key={school.id} value={school.name}>{school.name}</option>
        ))}
      </Select>
    </label>
  );
}

function PolicyPanel({ panel, onClose }: { panel: 'terms' | 'privacy'; onClose: () => void }) {
  const title = panel === 'terms' ? '이용약관' : '개인정보처리방침';
  const body = panel === 'terms'
    ? '서비스는 공공데이터 기반 주거 탐색 정보를 제공합니다. 데이터의 최신성·정확성은 원천 제공기관과 갱신 시점에 따라 달라질 수 있습니다.'
    : '회원 정보, 선택 입력 주소, 집 위치 좌표, 암호화된 AI API KEY를 서비스 제공 목적으로 처리합니다.';
  return (
    <div className="fixed inset-0 z-[1600] flex items-center justify-center bg-black/20 p-6" role="dialog" aria-modal="true" aria-label={title}>
      <section className="w-full max-w-[420px] rounded-card border border-border bg-[var(--map-guide-bg)] p-5 text-text shadow-xl backdrop-blur">
        <div className="flex items-start justify-between gap-3">
          <h2 className="m-0 text-card-heading font-semibold">{title}</h2>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px] text-text-muted">×</button>
        </div>
        <p className="m-0 mt-3 text-[13px] leading-6 text-text-muted">{body}</p>
      </section>
    </div>
  );
}
