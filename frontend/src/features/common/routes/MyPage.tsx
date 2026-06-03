import { useEffect, useState } from 'react';
import type { ClipboardEvent, FormEvent, ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Navigate, useNavigate } from 'react-router-dom';

import { Button, Input, Select } from '@/features/common/components/ui';
import { useAuth } from '@/features/common/contexts/AuthContext';
import {
  deleteAIAPIKey,
  deleteMe,
  getAIAPIKeys,
  getAIContextPreference,
  getUniversityOptions,
  patchMe,
  saveAIAPIKey,
  updateAIContextPreference,
} from '@/features/common/lib/api';
import type { AIProvider, MeResponse } from '@/features/common/types/api';

const PROVIDER_LABELS: Record<AIProvider, string> = {
  mindlogic: 'Mindlogic',
  openai: 'OpenAI',
};

type MyPageMode = 'view' | 'profile' | 'ai-key';
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
    return <Navigate to="/select?auth=login" replace />;
  }

  const handleLogout = async () => {
    await logout();
    if (onClose) {
      onClose();
      return;
    }
    navigate('/select', { replace: true });
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
            <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
              <Button type="button" variant="secondary" size="sm" onClick={() => setMode('ai-key')}>
                AI API KEY 설정
              </Button>
              <span className="text-[13px] font-semibold text-text-subtle" aria-hidden="true">|</span>
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

        {!requiresEmail && mode === 'ai-key' ? (
          <AIKeyEditor onBack={() => setMode('view')} />
        ) : null}
      {withdrawOpen ? (
        <WithdrawModal
          onClose={() => setWithdrawOpen(false)}
          onDone={() => {
            if (onClose) {
              onClose();
              return;
            }
            navigate('/select?auth=login&withdrawn=1', { replace: true });
          }}
        />
      ) : null}
    </section>
  );
}

export default function MyPage() {
  return <Navigate to="/select?auth=mypage" replace />;
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
            <p className="m-0 mt-2 text-[13px] leading-6 text-text-muted">계정, 프로필, 집 주소/좌표, 저장된 AI API KEY가 삭제됩니다. 이 작업은 되돌릴 수 없습니다.</p>
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

function AIKeyEditor({ onBack }: { onBack: () => void }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['ai-api-keys'], queryFn: getAIAPIKeys });
  const [provider, setProvider] = useState<AIProvider>('mindlogic');
  const [priority, setPriority] = useState(1);
  const [apiKey, setApiKey] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [passphraseConfirm, setPassphraseConfirm] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [guideOpen, setGuideOpen] = useState(false);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['ai-api-keys'] });
  const saveMutation = useMutation({
    mutationFn: saveAIAPIKey,
    onSuccess: () => {
      setApiKey('');
      setPassphrase('');
      setPassphraseConfirm('');
      setMessage('API KEY를 저장했습니다. 30분 동안 사용할 수 있습니다.');
      invalidate();
    },
    onError: () => setMessage('API KEY 저장에 실패했습니다.'),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteAIAPIKey,
    onSuccess: () => {
      setMessage('API KEY를 삭제했습니다.');
      invalidate();
    },
  });

  const handleSave = (event: FormEvent) => {
    event.preventDefault();
    if (!apiKey.trim() || !passphrase) {
      setMessage('API KEY와 복호화 문구를 입력해주세요.');
      return;
    }
    if (passphrase !== passphraseConfirm) {
      setMessage('복호화 문구가 서로 다릅니다.');
      return;
    }
    saveMutation.mutate({ provider, api_key: apiKey.trim(), passphrase, priority });
  };

  return (
    <section className="grid gap-4" aria-labelledby="ai-key-heading">
      <div className="pr-10">
        <div className="grid gap-2">
          <div className="flex items-center gap-2">
            <h1 id="ai-key-heading" className="m-0 text-section-display font-semibold leading-none text-text">AI API KEY 설정</h1>
            <button
              type="button"
              className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-border bg-surface-alt text-[13px] font-bold text-text-muted transition hover:border-primary hover:text-primary"
              onClick={() => setGuideOpen((open) => !open)}
              aria-label="API KEY 발급 안내"
              aria-expanded={guideOpen}
            >
              i
            </button>
          </div>
          <p className="m-0 mt-2 text-[13px] leading-5 text-text-muted">저장된 키는 복호화 문구로 30분 동안 열어 사용할 수 있습니다.</p>
        </div>
      </div>

      {guideOpen ? <AIKeyGuide /> : null}

      <div className="grid gap-2 rounded-card border border-border bg-surface-alt p-3">
        {isLoading ? <p className="m-0 text-caption text-text-muted">키 상태를 불러오는 중...</p> : null}
        {(data?.keys ?? []).map((item) => (
          <div key={item.provider} className="flex items-center justify-between gap-3 border-b border-divider py-2 last:border-b-0">
            <div>
              <strong className="block text-[13px] text-text">{PROVIDER_LABELS[item.provider]}</strong>
              <span className="text-[12px] text-text-muted">
                {item.configured ? `${item.masked_key} · 우선순위 ${item.priority ?? '-'}` : '미설정'}
                {item.unlocked ? ' · 사용 가능' : ''}
              </span>
            </div>
            {item.configured ? (
              <button type="button" className="text-[12px] font-semibold text-danger" onClick={() => deleteMutation.mutate(item.provider)}>삭제</button>
            ) : null}
          </div>
        ))}
      </div>

      <form className="grid gap-3" onSubmit={handleSave}>
        <div className="grid grid-cols-2 gap-2">
          <label className="grid gap-2 text-caption text-text">
            제공자
            <Select value={provider} onChange={(e) => setProvider(e.target.value as AIProvider)}>
              <option value="mindlogic">Mindlogic</option>
              <option value="openai">OpenAI</option>
            </Select>
          </label>
          <label className="grid gap-2 text-caption text-text">
            우선순위
            <Select value={String(priority)} onChange={(e) => setPriority(Number(e.target.value))}>
              <option value="1">1순위</option>
              <option value="2">2순위</option>
            </Select>
          </label>
        </div>
        <MaskedSecretInput label="API KEY" value={apiKey} onChange={setApiKey} placeholder="붙여넣거나 입력하면 가운데가 가려집니다" />
        <Input
          label="복호화 문구"
          type="password"
          name="slgi-ai-passphrase"
          autoComplete="new-password"
          value={passphrase}
          onChange={(e) => setPassphrase(e.target.value)}
          placeholder="키를 사용할 때 필요한 문구"
        />
        <Input
          label="복호화 문구 확인"
          type="password"
          name="slgi-ai-passphrase-confirm"
          autoComplete="new-password"
          value={passphraseConfirm}
          onChange={(e) => setPassphraseConfirm(e.target.value)}
          placeholder="같은 문구를 한 번 더 입력"
        />
        <div className="grid grid-cols-2 gap-2">
          <Button type="submit" variant="primary" size="sm" loading={saveMutation.isPending}>저장</Button>
          <Button type="button" variant="secondary" size="sm" onClick={onBack} disabled={saveMutation.isPending}>취소</Button>
        </div>
      </form>
      {message ? <p className="m-0 text-caption text-text-muted">{message}</p> : null}
    </section>
  );
}

function AIKeyGuide() {
  return (
    <aside className="grid gap-3 rounded-card border border-border bg-surface-alt p-4 text-[13px] leading-6 text-text-muted">
      <div>
        <h2 className="m-0 text-[14px] font-semibold text-text">Mindlogic API KEY</h2>
        <ol className="m-0 mt-2 grid gap-1 pl-5">
          <li>
            <a
              href="https://aichat.dongguk.edu/"
              target="_blank"
              rel="noreferrer"
              className="font-semibold text-primary hover:text-primary-hover"
            >
              동국대 AI Chat
            </a>
            에 접속합니다.
          </li>
          <li>우측 하단의 API Gateway를 클릭합니다.</li>
          <li>+ API KEY 생성을 클릭합니다.</li>
          <li>생성된 키 값을 복사해 이 화면의 API KEY 입력칸에 붙여넣습니다.</li>
        </ol>
      </div>
      <div>
        <h2 className="m-0 text-[14px] font-semibold text-text">OpenAI API KEY</h2>
        <ol className="m-0 mt-2 grid gap-1 pl-5">
          <li>
            <a
              href="https://platform.openai.com/api-keys"
              target="_blank"
              rel="noreferrer"
              className="font-semibold text-primary hover:text-primary-hover"
            >
              OpenAI API keys
            </a>
            페이지에 로그인합니다.
          </li>
          <li>Create new secret key를 눌러 새 키를 생성합니다.</li>
          <li>생성 직후 한 번만 보이는 키 값을 복사해 이 화면의 API KEY 입력칸에 붙여넣습니다.</li>
          <li>OpenAI API 사용에는 별도 결제 설정 또는 크레딧이 필요할 수 있습니다.</li>
        </ol>
      </div>
    </aside>
  );
}

function maskSecret(value: string): string {
  if (!value) return '';
  if (value.length <= 4) return '*'.repeat(value.length);
  return `${value.slice(0, 2)}${'*'.repeat(Math.max(3, value.length - 4))}${value.slice(-2)}`;
}

function MaskedSecretInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const handlePaste = (event: ClipboardEvent<HTMLInputElement>) => {
    event.preventDefault();
    const pasted = event.clipboardData.getData('text');
    onChange(pasted);
  };

  return (
    <label className="grid gap-2 text-caption text-text">
      {label}
      <input
        type="text"
        name="slgi-ai-key"
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        inputMode="text"
        value={maskSecret(value)}
        onPaste={handlePaste}
        onChange={(event) => {
          const next = event.target.value;
          if (next.includes('*')) return;
          onChange(next);
        }}
        onKeyDown={(event) => {
          if (event.key === 'Backspace' || event.key === 'Delete') onChange('');
        }}
        placeholder={placeholder}
        className="h-11 rounded-sm border border-border bg-surface px-3 text-[15px] font-medium text-text outline-none transition placeholder:text-text-subtle focus:border-primary"
      />
    </label>
  );
}
