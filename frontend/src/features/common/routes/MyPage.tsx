import { useEffect, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Navigate, useNavigate } from 'react-router-dom';

import { Button, Input, Select } from '@/features/common/components/ui';
import { useAuth } from '@/features/common/contexts/AuthContext';
import {
  deleteMe,
  getAIContextPreference,
  getUniversityOptions,
  patchMe,
  updateAIContextPreference,
} from '@/features/common/lib/api';
import type { MeResponse } from '@/features/common/types/api';

type MyPageMode = 'view' | 'profile';
const WITHDRAW_CONFIRM_TEXT = '자취맵 탈퇴';

export function MyPagePanel({ onClose }: { onClose?: () => void } = {}) {
  const navigate = useNavigate();
  const { user, isLoading, logout } = useAuth();
  const [mode, setMode] = useState<MyPageMode>('view');
  const [withdrawOpen, setWithdrawOpen] = useState(false);

  useEffect(() => {
    if (!withdrawOpen) return;
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      setWithdrawOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [withdrawOpen]);

  if (isLoading) {
    return <section className="p-8 text-center text-text-muted">불러오는 중...</section>;
  }
  if (!user) {
    return <Navigate to="/recommend/conditions?auth=login" replace />;
  }

  const handleLogout = async () => {
    await logout();
    if (onClose) {
      onClose();
      return;
    }
    navigate('/recommend/conditions', { replace: true });
  };
  const requiresEmail = !user.email?.trim();

  return (
    <section className="relative flex w-full flex-col gap-5 p-8 text-text" aria-labelledby="mypage-title">
        {requiresEmail ? (
          <RequiredEmailForm onSaved={() => setMode('view')} />
        ) : null}

        {!requiresEmail && mode === 'view' ? (
          <>
            <ProfileSummary user={user} />
            <Divider />
            <div className="flex">
              <Button type="button" variant="secondary" size="sm" onClick={() => setMode('profile')}>
                프로필 편집
              </Button>
            </div>
            <Divider />
            <div className="grid grid-cols-2 gap-2">
              <LogoutButton onClick={handleLogout} />
              <button
                type="button"
                onClick={() => setWithdrawOpen(true)}
                className="h-10 rounded-sm border border-border bg-surface-alt px-4 text-[13px] font-semibold text-text-muted transition hover:border-danger hover:bg-danger hover:text-white"
              >
                회원탈퇴
              </button>
            </div>
          </>
        ) : null}

        {!requiresEmail && mode === 'profile' ? (
          <ProfileEditForm user={user} onCancel={() => setMode('view')} onSaved={() => setMode('view')} />
        ) : null}

      {withdrawOpen ? (
        <WithdrawModal
          onClose={() => setWithdrawOpen(false)}
          onDone={() => {
            if (onClose) {
              onClose();
              return;
            }
            navigate('/recommend/conditions?auth=login&withdrawn=1', { replace: true });
          }}
        />
      ) : null}
    </section>
  );
}

export default function MyPage() {
  return <Navigate to="/recommend/conditions?auth=mypage" replace />;
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function RequiredEmailForm({ onSaved }: { onSaved: () => void }) {
  const { refresh } = useAuth();
  const [email, setEmail] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = email.trim();
    if (!EMAIL_PATTERN.test(trimmed)) {
      setError('올바른 이메일 주소를 입력해주세요.');
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await patchMe({ email: trimmed });
      await refresh();
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : '이메일 저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="grid gap-5" onSubmit={handleSubmit}>
      <div>
        <h1 className="m-0 text-section-display font-semibold leading-none text-text">이메일 입력</h1>
        <p className="m-0 mt-3 text-[13px] leading-6 text-text-muted">
          카카오에서 이메일 제공을 사용할 수 없어 서비스 안내와 계정 관리를 위한 이메일을 직접 입력해야 합니다.
        </p>
      </div>
      <Input
        label="이메일"
        type="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        placeholder="example@email.com"
        autoComplete="email"
        error={error ?? undefined}
        required
      />
      <Button type="submit" variant="primary" size="sm" loading={saving}>저장하고 계속하기</Button>
    </form>
  );
}

function Divider() {
  return <hr className="m-0 h-px border-none bg-divider" />;
}

function LogoutButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="h-10 rounded-sm border border-danger/30 bg-danger-soft px-4 text-[13px] font-semibold text-danger transition hover:border-danger hover:bg-danger/10"
    >
      로그아웃
    </button>
  );
}

function WithdrawModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const { logout } = useAuth();
  const [confirmText, setConfirmText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const canSubmit = confirmText.trim() === WITHDRAW_CONFIRM_TEXT;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit || submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      await deleteMe(confirmText.trim());
      await logout();
      onDone();
    } catch {
      setError('회원탈퇴에 실패했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[1700] flex items-center justify-center bg-black/25 p-6" role="dialog" aria-modal="true" aria-label="회원탈퇴">
      <form className="grid w-full max-w-[440px] gap-4 rounded-card border border-danger/30 bg-surface p-5 text-text shadow-xl" onSubmit={handleSubmit}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="m-0 text-card-heading font-semibold">회원탈퇴</h2>
            <p className="m-0 mt-2 text-[13px] leading-6 text-text-muted">계정, 프로필, 집 주소/좌표가 삭제됩니다. 이 작업은 되돌릴 수 없습니다.</p>
          </div>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px] text-text-muted" aria-label="닫기">×</button>
        </div>
        <Input
          label={`확인 문구: ${WITHDRAW_CONFIRM_TEXT}`}
          value={confirmText}
          onChange={(event) => setConfirmText(event.target.value)}
          placeholder={WITHDRAW_CONFIRM_TEXT}
        />
        {error ? <p className="m-0 text-caption text-danger">{error}</p> : null}
        <div className="grid grid-cols-2 gap-2">
          <button
            type="submit"
            disabled={!canSubmit || submitting}
            className="inline-flex h-8 items-center justify-center rounded-md border border-border bg-surface-alt px-4 text-[13px] font-semibold text-text-muted transition-colors hover:enabled:border-danger hover:enabled:bg-danger hover:enabled:text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? '처리 중...' : '탈퇴하기'}
          </button>
          <Button type="button" variant="secondary" size="sm" onClick={onClose} disabled={submitting}>취소</Button>
        </div>
      </form>
    </div>
  );
}

function ProfileSummary({ user }: { user: MeResponse }) {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['ai-context-preferences'],
    queryFn: getAIContextPreference,
    staleTime: 60_000,
  });
  const mutation = useMutation({
    mutationFn: updateAIContextPreference,
    onSuccess: (next) => {
      queryClient.setQueryData(['ai-context-preferences'], next);
    },
  });

  const display = user.nickname?.trim() || user.username;
  const school = user.school?.trim() || '\ub300\ud559 \ubbf8\uc785\ub825';
  const year = user.year != null ? `${user.year}\ud559\ub144` : '\ud559\ub144 \ubbf8\uc785\ub825';
  const address = user.address?.trim() || '\uc8fc\uc18c \ubbf8\uc785\ub825';
  const schoolAvailable = Boolean(data?.school_available ?? user.school?.trim());
  const homeAvailable = Boolean(data?.home_location_available ?? (typeof user.home_lat === 'number' && typeof user.home_lng === 'number'));
  const busy = isLoading || mutation.isPending;

  return (
    <header className="grid gap-4 text-left">
      <div>
        <h1 id="mypage-title" className="m-0 text-section-display font-semibold leading-none text-text">{display}</h1>
        <div className="mt-4 grid gap-1.5 text-[16px] leading-7 text-text-muted">
          <ProfileConsentRow
            text={school}
            label="AI school context consent"
            checked={Boolean(data?.share_school_with_ai)}
            disabled={!schoolAvailable || busy}
            onChange={(checked) => mutation.mutate({ share_school_with_ai: checked })}
          />
          <span>{year}</span>
          <ProfileConsentRow
            text={address}
            label="AI home location context consent"
            checked={Boolean(data?.share_home_location_with_ai)}
            disabled={!homeAvailable || busy}
            onChange={(checked) => mutation.mutate({ share_home_location_with_ai: checked })}
          />
        </div>
      </div>
      <div className="grid gap-1 text-[12px] leading-5 text-text-muted">
        <p className="m-0">{'\ub3d9\uc758\ud558\uba74 \uc800\uc7a5\ub41c \ub300\ud559\uacfc \uc9d1 \uc704\uce58 \uc88c\ud45c\uac00 AI \uc9c8\ubb38 \ucc98\ub9ac\uc5d0 \ud568\uaed8 \uc0ac\uc6a9\ub429\ub2c8\ub2e4.'}</p>
        <p className="m-0">{'\ub3d9\uc758\ud558\uc9c0 \uc54a\uc740 \uc815\ubcf4\ub294 \uc804\ub2ec\ud558\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4.'}</p>
        {isError ? <p className="m-0 text-danger">{'AI \uc815\ubcf4 \uc81c\uacf5 \uc124\uc815\uc744 \ubd88\ub7ec\uc624\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.'}</p> : null}
        {mutation.isError ? <p className="m-0 text-danger">{'AI \uc815\ubcf4 \uc81c\uacf5 \uc124\uc815 \uc800\uc7a5\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.'}</p> : null}
      </div>
    </header>
  );
}

function ProfileConsentRow({
  text,
  label,
  checked,
  disabled,
  onChange,
}: {
  text: string;
  label: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <span className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
      <span className="min-w-0 truncate">{text}</span>
      <input
        type="checkbox"
        className="h-5 w-5 shrink-0 accent-primary"
        aria-label={label}
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
    </span>
  );
}

const YEAR_OPTIONS = [
  { value: '', label: '학년 미입력' },
  { value: '1', label: '1학년' },
  { value: '2', label: '2학년' },
  { value: '3', label: '3학년' },
  { value: '4', label: '4학년' },
  { value: '5', label: '5학년 이상' },
];

function UniversitySelect({
  value,
  onChange,
  label = '다니는 대학',
}: {
  value: string;
  onChange: (value: string) => void;
  label?: ReactNode;
}) {
  const { data, isLoading } = useQuery({ queryKey: ['universities'], queryFn: getUniversityOptions, staleTime: 60 * 60 * 1000 });
  const schools = data?.schools ?? [];
  const hasCurrent = value === '' || schools.some((school) => school.name === value);

  return (
    <label className="grid gap-2 text-caption text-text">
      {label}
      <Select value={value} onChange={(e) => onChange(e.target.value)} disabled={isLoading}>
        <option value="">{isLoading ? '대학 목록 불러오는 중' : '대학 미입력'}</option>
        {!hasCurrent ? <option value={value}>{value}</option> : null}
        {schools.map((school) => (
          <option key={school.id} value={school.name}>{school.name}</option>
        ))}
      </Select>
    </label>
  );
}

function ProfileEditForm({ user, onCancel, onSaved }: { user: MeResponse; onCancel: () => void; onSaved: () => void }) {
  const { refresh } = useAuth();
  const [nickname, setNickname] = useState(user.nickname ?? '');
  const [school, setSchool] = useState(user.school ?? '');
  const [year, setYear] = useState(user.year != null ? String(user.year) : '');
  const [address, setAddress] = useState(user.address ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await patchMe({
        nickname: nickname.trim(),
        school: school.trim(),
        year: year === '' ? null : Number(year),
        address: address.trim(),
      });
      await refresh();
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : '저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="grid gap-4" onSubmit={handleSubmit}>
      <h1 className="m-0 text-section-display font-semibold leading-none text-text">프로필 편집</h1>
      <Input label="닉네임" value={nickname} onChange={(e) => setNickname(e.target.value)} maxLength={30} />
      <UniversitySelect value={school} onChange={setSchool} />
      <label className="grid gap-2 text-caption text-text">
        학년
        <Select value={year} onChange={(e) => setYear(e.target.value)}>
          {YEAR_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
        </Select>
      </label>
      <Input label="주소" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="예: 서울특별시 중구 세종대로 110" />
      {error ? <p className="m-0 text-caption text-danger">{error}</p> : null}
      <div className="grid grid-cols-2 gap-2">
        <Button type="submit" variant="primary" size="sm" loading={saving}>저장</Button>
        <Button type="button" variant="secondary" size="sm" onClick={onCancel} disabled={saving}>취소</Button>
      </div>
    </form>
  );
}
