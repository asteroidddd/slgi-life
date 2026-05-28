import { useEffect, useState } from 'react';
import type { ClipboardEvent, FormEvent, ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import { Button, Input, Select } from '@/components/ui';
import { useAuth } from '@/contexts/AuthContext';
import {
  deleteAIAPIKey,
  getAIAPIKeys,
  getUniversityOptions,
  patchMe,
  saveAIAPIKey,
  unlockAIAPIKeys,
} from '@/lib/api';
import type { AIProvider, MeResponse } from '@/types/api';

const PROVIDER_LABELS: Record<AIProvider, string> = {
  mindlogic: 'Mindlogic',
  openai: 'OpenAI',
};

type MyPageMode = 'view' | 'profile' | 'ai-key';
type LegalPanel = 'terms' | 'privacy' | 'data' | null;

export default function MyPage() {
  const navigate = useNavigate();
  const { user, isLoading, logout } = useAuth();
  const [mode, setMode] = useState<MyPageMode>('view');
  const [legalPanel, setLegalPanel] = useState<LegalPanel>(null);

  useEffect(() => {
    if (!legalPanel) return;
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      setLegalPanel(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [legalPanel]);

  if (isLoading) {
    return <main className="min-h-screen bg-primary-soft p-8 text-center text-text-muted">불러오는 중...</main>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <main className="relative flex min-h-screen items-center justify-center bg-primary-soft p-6 text-text" id="main">
      <Link to="/" className="app-floating-button absolute left-5 top-5 h-10 min-h-10 no-underline">
        맵으로 가기
      </Link>

      <section className="flex w-full max-w-[560px] flex-col gap-5 rounded-card border border-border bg-surface p-8 shadow-sm" aria-labelledby="mypage-title">
        {mode === 'view' ? (
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
            <LogoutButton onClick={handleLogout} />
            <LegalLinks onOpen={setLegalPanel} />
          </>
        ) : null}

        {mode === 'profile' ? (
          <ProfileEditForm user={user} onCancel={() => setMode('view')} onSaved={() => setMode('view')} />
        ) : null}

        {mode === 'ai-key' ? (
          <AIKeyEditor onBack={() => setMode('view')} />
        ) : null}
      </section>

      {legalPanel ? <LegalModal panel={legalPanel} onClose={() => setLegalPanel(null)} /> : null}
    </main>
  );
}

function LegalLinks({ onOpen }: { onOpen: (panel: Exclude<LegalPanel, null>) => void }) {
  return (
    <nav className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[12px] font-semibold leading-5 text-text-muted" aria-label="정책 링크">
      <button type="button" className="bg-transparent p-0 hover:text-text" onClick={() => onOpen('terms')}>이용약관</button>
      <button type="button" className="bg-transparent p-0 hover:text-text" onClick={() => onOpen('privacy')}>개인정보처리방침</button>
      <button type="button" className="bg-transparent p-0 hover:text-text" onClick={() => onOpen('data')}>데이터 출처</button>
    </nav>
  );
}

function LegalModal({ panel, onClose }: { panel: Exclude<LegalPanel, null>; onClose: () => void }) {
  const title = panel === 'terms' ? '이용약관' : panel === 'privacy' ? '개인정보처리방침' : '데이터 출처';
  return (
    <div className="fixed inset-0 z-[1600] flex items-center justify-center bg-black/20 p-6" role="dialog" aria-modal="true" aria-label={title}>
      <section className="w-full max-w-[420px] rounded-card border border-border bg-[var(--map-guide-bg)] p-5 text-text shadow-xl backdrop-blur">
        <div className="flex items-start justify-between gap-3">
          <h2 className="m-0 text-card-heading font-semibold">{title}</h2>
          <button type="button" onClick={onClose} className="h-8 w-8 rounded-[6px] bg-surface-alt text-[18px] text-text-muted" aria-label="닫기">×</button>
        </div>
        {panel === 'terms' ? (
          <p className="m-0 mt-3 text-[13px] leading-6 text-text-muted">서비스는 공공데이터 기반 주거 탐색 정보를 제공합니다. 데이터의 최신성, 정확성은 원천 제공기관과 갱신 시점에 따라 달라질 수 있으며, 사용자는 이를 참고 정보로 사용합니다.</p>
        ) : null}
        {panel === 'privacy' ? (
          <p className="m-0 mt-3 text-[13px] leading-6 text-text-muted">회원 정보, 선택 입력 주소, 집 위치 좌표, 암호화된 AI API KEY를 서비스 제공 목적으로 처리합니다. AI API KEY는 사용자의 복호화 문구 없이는 서버 단독으로 사용할 수 없고, 7일 이상 로그인 기록이 없으면 삭제됩니다.</p>
        ) : null}
        {panel === 'data' ? (
          <ul className="mt-3 grid gap-1 pl-4 text-[13px] leading-6 text-text-muted">
            <li>지도 타일, 검색, 좌표 변환: V-World</li>
            <li>행정동/법정동 경계: V-World 행정구역 경계 데이터</li>
            <li>실거래, 상권, 대중교통 등: 공공데이터포털, 서울 열린데이터광장</li>
            <li>안전 지표, 전월세전환율: KOSIS 기반</li>
          </ul>
        ) : null}
      </section>
    </div>
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

function ProfileSummary({ user }: { user: MeResponse }) {
  const display = user.nickname?.trim() || user.username;
  const school = user.school?.trim() || '대학 미입력';
  const year = user.year != null ? `${user.year}학년` : '학년 미입력';
  const address = user.address?.trim() || '주소 미입력';

  return (
    <header className="grid gap-5 text-left">
      <div>
        <h1 id="mypage-title" className="m-0 text-section-display font-semibold leading-none text-text">{display}</h1>
        <div className="mt-4 grid gap-1.5 text-[16px] leading-7 text-text-muted">
          <span>{school}</span>
          <span>{year}</span>
          <span>{address}</span>
        </div>
      </div>
    </header>
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
  const [message, setMessage] = useState<string | null>(null);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['ai-api-keys'] });
  const saveMutation = useMutation({
    mutationFn: saveAIAPIKey,
    onSuccess: () => {
      setApiKey('');
      setPassphrase('');
      setMessage('API KEY를 저장했습니다. 30분 동안 사용할 수 있습니다.');
      invalidate();
    },
    onError: () => setMessage('API KEY 저장에 실패했습니다.'),
  });
  const unlockMutation = useMutation({
    mutationFn: unlockAIAPIKeys,
    onSuccess: () => {
      setMessage('저장된 API KEY를 30분 동안 사용할 수 있게 열었습니다.');
      invalidate();
    },
    onError: () => setMessage('복호화 문구가 맞지 않습니다.'),
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
    saveMutation.mutate({ provider, api_key: apiKey.trim(), passphrase, priority });
  };

  return (
    <section className="grid gap-4" aria-labelledby="ai-key-heading">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 id="ai-key-heading" className="m-0 text-section-display font-semibold leading-none text-text">AI API KEY 설정</h1>
          <p className="m-0 mt-2 text-[13px] leading-5 text-text-muted">저장된 키는 복호화 문구로 30분 동안 열어 사용할 수 있습니다.</p>
        </div>
        <Button type="button" variant="secondary" size="sm" onClick={onBack}>돌아가기</Button>
      </div>

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
        <div className="grid grid-cols-2 gap-2">
          <Button type="submit" variant="primary" size="sm" loading={saveMutation.isPending}>저장</Button>
          <Button type="button" variant="secondary" size="sm" onClick={() => unlockMutation.mutate(passphrase)} loading={unlockMutation.isPending}>30분 열기</Button>
        </div>
      </form>
      {message ? <p className="m-0 text-caption text-text-muted">{message}</p> : null}
    </section>
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
