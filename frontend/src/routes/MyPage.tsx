// MyPage (`/mypage`) — SPEC 6.6.
//
// R-4 (design-polish-v2.md): rebuilt as a 2-column workspace.
//   LEFT rail (sticky)   — Profile + MY WEIGHTS
//   RIGHT column (scroll) — MY FAVORITES + MY REVIEWS
import { useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { Badge, Button, Input, MetricBar, Select } from '@/components/ui';
import { useAuth } from '@/contexts/AuthContext';
import { useFavorites, useRemoveFavorite } from '@/hooks/useFavorites';
import { patchMe } from '@/lib/api';
import type { FavoriteItem, MeResponse } from '@/types/api';

const MAX_COMPARE = 3;

export default function MyPage() {
  const navigate = useNavigate();
  const { user, isLoading, logout } = useAuth();

  if (isLoading) {
    return (
      <main className="min-h-screen bg-bg text-text" id="main">
        <div className="py-6 px-4 text-center text-body-base text-text-muted tracking-normal" role="status" aria-live="polite">
          불러오는 중…
        </div>
      </main>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <main className="min-h-screen bg-bg text-text" id="main">
      <h1 className="sr-only">마이페이지</h1>

      <div className="max-w-[1100px] mx-auto pt-4 px-6 flex justify-end">
        <Button variant="ghost" size="sm" onClick={handleLogout}>
          로그아웃
        </Button>
      </div>

      <div className="max-w-[1100px] mx-auto p-6 flex items-start gap-10 max-[1080px]:flex-col">
        <aside className="flex-[0_0_360px] max-w-[360px] sticky top-[calc(56px+var(--space-6))] self-start flex flex-col gap-10 max-[1080px]:static max-[1080px]:flex-[0_0_auto] max-[1080px]:max-w-none max-[1080px]:w-full" aria-label="프로필 및 가중치">
          <ProfileSection user={user} />
          <PreferenceSection user={user} />
        </aside>
        <div className="flex-auto max-w-[720px] flex flex-col gap-10 min-w-0 max-[1080px]:max-w-none">
          <FavoritesSection />
        </div>
      </div>
    </main>
  );
}

function ProfileSection({ user }: { user: MeResponse }) {
  const [editing, setEditing] = useState(false);

  return (
    <section className="flex flex-col gap-2" aria-labelledby="profile-heading">
      <p className="mono-label" aria-hidden="true">PROFILE</p>
      {editing ? (
        <ProfileEditForm
          user={user}
          onCancel={() => setEditing(false)}
          onSaved={() => setEditing(false)}
        />
      ) : (
        <ProfileView user={user} onEdit={() => setEditing(true)} />
      )}
    </section>
  );
}

function ProfileView({ user, onEdit }: { user: MeResponse; onEdit: () => void }) {
  const display = (user.nickname && user.nickname.trim()) || user.username;
  const meta: string[] = [];
  if (user.school && user.school.trim()) meta.push(user.school);
  if (user.year != null) meta.push(`${user.year}학년`);

  return (
    <>
      <h2 id="profile-heading" className="m-0 text-page-display leading-[1] font-bold text-text tracking-[-1.2px]">
        {display}
      </h2>
      <p className="m-0 text-body-base leading-[1.6] text-text-subtle tracking-normal">
        {meta.length > 0 ? meta.join(' · ') : '학교·학년 정보를 추가해주세요.'}
      </p>
      <div>
        <Button variant="secondary" size="sm" onClick={onEdit}>
          수정
        </Button>
      </div>
    </>
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

interface ProfileEditFormProps {
  user: MeResponse;
  onCancel: () => void;
  onSaved: () => void;
}

function ProfileEditForm({ user, onCancel, onSaved }: ProfileEditFormProps) {
  const { refresh } = useAuth();
  const [nickname, setNickname] = useState(user.nickname);
  const [school, setSchool] = useState(user.school);
  const [year, setYear] = useState<string>(
    user.year != null ? String(user.year) : '',
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await patchMe({
        nickname: nickname.trim(),
        school: school.trim(),
        year: year === '' ? null : Number(year),
      });
      await refresh();
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : '저장에 실패했어요.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
      <h2 id="profile-heading" className="sr-only">
        프로필 수정
      </h2>
      <label className="flex flex-col gap-1">
        <span className="text-caption text-text-muted tracking-normal">닉네임</span>
        <Input
          name="nickname"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          placeholder="예: jihyeon"
          maxLength={20}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-caption text-text-muted tracking-normal">학교</span>
        <Input
          name="school"
          value={school}
          onChange={(e) => setSchool(e.target.value)}
          placeholder="예: 동국대"
          maxLength={30}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-caption text-text-muted tracking-normal">학년</span>
        <Select
          name="year"
          value={year}
          onChange={(e) => setYear(e.target.value)}
        >
          {YEAR_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
      </label>
      {error && (
        <p className="m-0 text-caption text-danger tracking-normal" role="alert">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <Button type="submit" variant="primary" size="sm" loading={saving}>
          저장
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={onCancel}
          disabled={saving}
        >
          취소
        </Button>
      </div>
    </form>
  );
}

const DEFAULT_W = { rent: 33, amenity: 33, transit: 34 };

function PreferenceSection({ user }: { user: MeResponse }) {
  const navigate = useNavigate();
  const { w_rent, w_amenity, w_transit } = user.preference;

  const isDefault =
    w_rent === DEFAULT_W.rent &&
    w_amenity === DEFAULT_W.amenity &&
    w_transit === DEFAULT_W.transit;

  const handleStartLearning = () => navigate('/?onboarding=1');
  const handleRelearn = () => navigate('/?onboarding=1');

  if (isDefault) {
    return (
      <section className="flex flex-col gap-3" aria-labelledby="weights-heading">
        <p className="mono-label" aria-hidden="true">MY WEIGHTS</p>
        <h2 id="weights-heading" className="m-0 text-card-heading leading-[1.2] font-semibold text-text tracking-[-0.28px]">
          내 자취 기준
        </h2>
        <div className="py-5 flex flex-col gap-2">
          <p className="m-0 text-body-base text-text-muted tracking-normal">
            선호 학습을 시작하면 자동으로 채워져요.
          </p>
          <div>
            <Button variant="primary" size="sm" onClick={handleStartLearning}>
              선호 학습 시작 →
            </Button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-3" aria-labelledby="weights-heading">
      <p className="mono-label" aria-hidden="true">MY WEIGHTS</p>
      <h2 id="weights-heading" className="m-0 text-card-heading leading-[1.2] font-semibold text-text tracking-[-0.28px]">
        내 자취 기준
      </h2>
      <div className="flex flex-col gap-3">
        <MetricBar label="전월세" value={w_rent} tone="weight" unit="%" />
        <MetricBar label="생활시설" value={w_amenity} tone="weight" unit="%" />
        <MetricBar label="교통" value={w_transit} tone="weight" unit="%" />
      </div>
      <div>
        <Button variant="secondary" size="sm" onClick={handleRelearn}>
          선호 학습 다시 →
        </Button>
      </div>
    </section>
  );
}

function FavoritesSection() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useFavorites();
  const removeMut = useRemoveFavorite();

  const items: FavoriteItem[] = data ?? [];

  const compareSlugs = useMemo(
    () => items.slice(0, MAX_COMPARE).map((f) => f.slug),
    [items],
  );

  const handleCompareAll = () => {
    if (compareSlugs.length === 0) return;
    navigate(`/compare?adongs=${compareSlugs.join(',')}`);
  };

  return (
    <section className="flex flex-col gap-4" aria-labelledby="favorites-heading">
      <p className="mono-label" aria-hidden="true">MY FAVORITES</p>
      <header className="flex items-baseline justify-between gap-3 flex-wrap">
        <h2 id="favorites-heading" className="m-0 text-card-heading leading-[1.2] font-semibold text-text tracking-[-0.28px]">
          찜한 동네
          {items.length > 0 && (
            <span className="text-text-subtle font-normal tabular"> ({items.length})</span>
          )}
        </h2>
        {items.length >= 2 && (
          <button
            type="button"
            className="bg-none border-none py-1 px-2 rounded-sm text-caption text-link font-medium tracking-normal cursor-pointer transition-all duration-[120ms] ease-out hover:bg-primary-soft hover:underline hover:underline-offset-2 focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2"
            onClick={handleCompareAll}
          >
            {Math.min(items.length, MAX_COMPARE)}개 모두 비교하기 →
          </button>
        )}
      </header>

      {isLoading && (
        <div className="py-6 px-4 text-center text-body-base text-text-muted tracking-normal" role="status">
          찜 목록을 불러오는 중…
        </div>
      )}

      {isError && (
        <div className="py-6 px-4 text-center text-danger flex flex-col items-center gap-2" role="alert">
          찜 목록을 불러오지 못했어요.
          <span className="text-caption text-text-muted">
            {error instanceof Error ? error.message : '알 수 없는 오류'}
          </span>
        </div>
      )}

      {!isLoading && !isError && items.length === 0 && (
        <div className="py-5 flex flex-col gap-2">
          <p className="m-0 text-body-base text-text-muted tracking-normal">아직 찜한 동네가 없어요.</p>
          <div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate('/')}
            >
              메인 지도 →
            </Button>
          </div>
        </div>
      )}

      {items.length > 0 && (
        <ul className="list-none m-0 p-0">
          {items.map((fav) => (
            <FavoriteRow
              key={fav.slug}
              item={fav}
              onOpen={() => navigate(`/adong/${fav.slug}`)}
              onConfirmRemove={() => removeMut.mutate(fav.slug)}
              removing={removeMut.isPending && removeMut.variables === fav.slug}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

interface FavoriteRowProps {
  item: FavoriteItem;
  onOpen: () => void;
  onConfirmRemove: () => void;
  removing: boolean;
}

function FavoriteRow({
  item,
  onOpen,
  onConfirmRemove,
  removing,
}: FavoriteRowProps) {
  const score = Math.round(item.score);
  const variant = score >= 70 ? 'success' : score >= 40 ? 'warning' : 'danger';
  const [confirming, setConfirming] = useState(false);

  return (
    <li className="group flex items-stretch border-b border-divider last:border-b-0 transition-all duration-[120ms] ease-out hover:bg-surface-alt">
      <button
        type="button"
        className="flex-1 flex items-center justify-between gap-3 py-4 bg-none border-none cursor-pointer text-left text-inherit tracking-normal focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-[-2px]"
        onClick={onOpen}
        aria-label={`${item.name} 상세 보기`}
      >
        <div className="flex flex-col gap-[2px]">
          <span className="text-caption text-text-muted">{item.gu}</span>
          <span className="text-feature-heading font-semibold leading-[1.3] text-text">{item.name}</span>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={variant}>{score}점</Badge>
          <span className="text-caption text-text-subtle tabular">{formatDate(item.created_at)}</span>
        </div>
      </button>
      {confirming ? (
        <span className="self-center inline-flex items-center gap-2 py-1 px-2 text-caption text-text tracking-normal" role="alertdialog" aria-label="찜 해제 확인">
          <span className="text-text-muted">확실해요?</span>
          <button
            type="button"
            className="appearance-none bg-transparent border border-border rounded-sm py-[2px] px-2 cursor-pointer text-caption text-text tracking-normal transition-all duration-[120ms] ease-out hover:bg-danger-soft hover:border-danger hover:text-danger focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-1 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={(e) => {
              e.stopPropagation();
              onConfirmRemove();
            }}
            disabled={removing}
          >
            예
          </button>
          <button
            type="button"
            className="appearance-none bg-transparent border border-border rounded-sm py-[2px] px-2 cursor-pointer text-caption text-text tracking-normal transition-all duration-[120ms] ease-out hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-1 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={(e) => {
              e.stopPropagation();
              setConfirming(false);
            }}
            disabled={removing}
          >
            아니요
          </button>
        </span>
      ) : (
        <button
          type="button"
          className="self-center inline-flex items-center gap-1 py-1 px-2 border-none bg-transparent text-text-muted cursor-pointer text-caption tracking-normal rounded-sm opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-all duration-[120ms] ease-out hover:bg-danger-soft hover:text-danger focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-1 focus-visible:opacity-100 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={(e) => {
            e.stopPropagation();
            setConfirming(true);
          }}
          aria-label={`${item.name} 찜 해제`}
          disabled={removing}
        >
          × 찜 해제
        </button>
      )}
    </li>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}.${mm}.${dd}`;
  } catch {
    return iso;
  }
}

