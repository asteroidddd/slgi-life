import { useEffect, useMemo, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import {
  getUniversityOptions,
  getUserRecommendationConditions,
  recommendRegions,
  saveUserRecommendationConditions,
} from '@/features/common/lib/api';
import { useAuth } from '@/features/common/contexts/AuthContext';
import {
  RECOMMENDATION_FACILITY_GROUPS,
  RECOMMENDATION_FACILITIES,
  type RecommendationFacilityKey,
  type RecommendationPriority,
  type RecommendationConditions as RecommendationConditionsState,
  loadRecommendationConditions,
  saveRecommendationConditions,
  saveRecommendationResults,
} from '@/features/recommendation/lib/recommendation';

export default function RecommendationConditions() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [deposit, setDeposit] = useState('5000');
  const [monthlyRent, setMonthlyRent] = useState('60');
  const [areaM2, setAreaM2] = useState('20');
  const [areaAny, setAreaAny] = useState(false);
  const [facilities, setFacilities] = useState<Set<RecommendationFacilityKey>>(new Set());
  const [universityId, setUniversityId] = useState('');
  const [maxCommuteMinutes, setMaxCommuteMinutes] = useState('30');
  const [priority, setPriority] = useState<RecommendationPriority>('budget');
  const [saving, setSaving] = useState(false);
  const [finding, setFinding] = useState(false);
  const [dialog, setDialog] = useState<{ title: string; message: string } | null>(null);
  const [conditionsLoaded, setConditionsLoaded] = useState(!user);
  const [userSchoolDefaultApplied, setUserSchoolDefaultApplied] = useState(false);

  const universitiesQuery = useQuery({
    queryKey: ['users', 'universities'],
    queryFn: getUniversityOptions,
    staleTime: 300_000,
  });

  const selectedUniversity = useMemo(
    () => universitiesQuery.data?.schools.find((school) => school.id === universityId) ?? null,
    [universityId, universitiesQuery.data?.schools],
  );

  const applyConditions = (conditions: RecommendationConditionsState) => {
    setDeposit(String(conditions.deposit || 0));
    setMonthlyRent(String(conditions.monthlyRent || 0));
    setAreaAny(conditions.areaM2 == null);
    setAreaM2(String(conditions.areaM2 ?? 20));
    setFacilities(new Set(
      conditions.facilities.filter((item): item is RecommendationFacilityKey =>
        RECOMMENDATION_FACILITIES.some((facility) => facility.key === item),
      ),
    ));
    setUniversityId(conditions.universityId || '');
    setUserSchoolDefaultApplied(Boolean(conditions.universityId));
    setMaxCommuteMinutes(String(conditions.maxCommuteMinutes || 30));
    setPriority(conditions.priority === 'transport' ? 'transport' : 'budget');
  };

  useEffect(() => {
    setUserSchoolDefaultApplied(false);
  }, [user?.id]);

  useEffect(() => {
    if (!user) {
      const localConditions = loadRecommendationConditions();
      if (localConditions) applyConditions(localConditions);
      setConditionsLoaded(true);
      return;
    }
    setConditionsLoaded(false);
    let cancelled = false;
    getUserRecommendationConditions()
      .then((data) => {
        if (cancelled || !data.conditions) return;
        const conditions = data.conditions as RecommendationConditionsState;
        applyConditions(conditions);
        saveRecommendationConditions(conditions as RecommendationConditionsState);
      })
      .catch(() => {
        const localConditions = loadRecommendationConditions();
        if (!cancelled && localConditions) applyConditions(localConditions);
      })
      .finally(() => {
        if (!cancelled) setConditionsLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  useEffect(() => {
    if (!conditionsLoaded || userSchoolDefaultApplied || universityId || !user?.school) return;
    const schools = universitiesQuery.data?.schools ?? [];
    if (schools.length === 0) return;
    const userSchoolName = normalizeSchoolName(user.school);
    const matchedSchool = schools.find((school) => normalizeSchoolName(school.name) === userSchoolName);
    if (matchedSchool) setUniversityId(matchedSchool.id);
    setUserSchoolDefaultApplied(true);
  }, [
    conditionsLoaded,
    universityId,
    universitiesQuery.data?.schools,
    user?.school,
    userSchoolDefaultApplied,
  ]);

  const toggleFacility = (key: RecommendationFacilityKey) => {
    setFacilities((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const buildConditions = (): RecommendationConditionsState => ({
    deposit: Number(deposit) || 0,
    monthlyRent: Number(monthlyRent) || 0,
    areaM2: areaAny ? null : Number(areaM2) || null,
    facilities: Array.from(facilities),
    universityId,
    universityName: selectedUniversity?.name ?? '',
    maxCommuteMinutes: Number(maxCommuteMinutes) || 0,
    priority,
  });

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setDialog(null);
    const conditions = buildConditions();
    saveRecommendationConditions(conditions);

    setFinding(true);
    try {
      const result = await recommendRegions(conditions);
      if (result.total === 0) {
        setDialog({
          title: '조건에 맞는 동네 없음',
          message: '입력한 예산, 통학 시간, 선호 시설을 모두 만족하는 동네가 없습니다. 조건을 조금 넓혀 다시 찾아보세요.',
        });
        return;
      }
      saveRecommendationResults(conditions, result);
      if (user) {
        setSaving(true);
        try {
          await saveUserRecommendationConditions(conditions);
        } catch {
          // Recommendation can continue; condition remains stored in session.
        } finally {
          setSaving(false);
        }
      }
      navigate('/recommend/results');
    } catch (error) {
      setDialog({
        title: '동네를 찾지 못했습니다',
        message: recommendationErrorMessage(error),
      });
    } finally {
      setFinding(false);
    }
  };

  const disabled = saving || finding;

  return (
    <main className="min-h-screen bg-primary-soft text-text">
      <form onSubmit={handleSubmit} className="mx-auto grid w-full max-w-[1120px] gap-5 px-6 pb-12 pt-24">
        <header className="flex items-start justify-between gap-6">
          <div>
            <h1 className="m-0 text-[34px] font-semibold leading-tight tracking-normal">조건 입력</h1>
            <p className="m-0 mt-2 text-[14px] leading-6 text-text-muted">
              예산, 통학 시간, 선호 시설을 기준으로 동네를 찾습니다. 추천 결과는 데이터 기반 참고 정보이며 실제 매물·교통·시설 현황과 다를 수 있습니다.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3" aria-label="우선순위">
            <span className="whitespace-nowrap text-[15px] font-bold text-text">우선순위</span>
            <div className="grid w-[210px] grid-cols-2 gap-1 rounded-sm border border-border bg-surface-alt p-1" role="group" aria-label="우선순위">
              <PriorityToggle active={priority === 'budget'} onClick={() => setPriority('budget')}>
                예산
              </PriorityToggle>
              <PriorityToggle active={priority === 'transport'} onClick={() => setPriority('transport')}>
                교통
              </PriorityToggle>
            </div>
          </div>
        </header>

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_400px]">
          <ConditionCard title="예산">
            <div className="grid grid-cols-2 gap-x-3 gap-y-4">
              <NumberField label="보증금" unit="만원" value={deposit} onChange={setDeposit} min={0} step={500} />
              <NumberField label="월세" unit="만원" value={monthlyRent} onChange={setMonthlyRent} min={0} step={5} />
              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="text-[13px] font-semibold text-text">집 크기</span>
                  <label className="flex items-center gap-2 text-[12px] font-semibold text-text-muted">
                    <input type="checkbox" checked={areaAny} onChange={(event) => setAreaAny(event.target.checked)} />
                    상관없음
                  </label>
                </div>
                <NumberInput
                  unit="m²"
                  value={areaM2}
                  onChange={setAreaM2}
                  min={0}
                  step={5}
                  disabled={areaAny}
                  suffix={formatPyeong(areaM2)}
                />
              </div>
              <p className="self-end text-[12px] font-semibold leading-5 text-text-muted">
                집 크기 입력 시 ㎡당 환산월세 기준, 상관없음 선택 시 환산월세 중위값 기준으로 계산합니다.
              </p>
            </div>
          </ConditionCard>

          <ConditionCard title="교통">
            <div className="grid gap-4">
              <label className="grid w-[calc(100%-32px)] max-w-full gap-2 text-[13px] font-semibold text-text">
                대학
                <select
                  value={universityId}
                  onChange={(event) => setUniversityId(event.target.value)}
                  className="h-11 w-full min-w-0 rounded-sm border border-border bg-surface-alt px-3 text-[14px] outline-none transition focus:border-primary"
                >
                  <option value="">대학 선택</option>
                  {(universitiesQuery.data?.schools ?? []).map((school) => (
                    <option key={school.id} value={school.id}>
                      {school.name}
                    </option>
                  ))}
                </select>
                {universitiesQuery.isError ? (
                  <span className="text-[12px] font-normal text-danger">대학 목록을 불러오지 못했습니다.</span>
                ) : null}
              </label>
              <CommuteTimeField value={maxCommuteMinutes} onChange={setMaxCommuteMinutes} />
            </div>
          </ConditionCard>
        </section>

        <section className="rounded-sm border border-border bg-surface p-6 shadow-floating">
          <div className="flex items-center justify-between gap-4 border-b border-border pb-4">
            <div>
              <h2 className="m-0 text-[22px] font-semibold">선호 시설</h2>
              <p className="m-0 mt-1 text-[12px] font-semibold text-text-muted">복수 선택 가능. 선택한 시설이 있는 동네만 후보에 포함합니다.</p>
            </div>
            <span className="rounded-sm bg-surface-alt px-3 py-1 text-[12px] font-bold text-text-muted">{facilities.size}개 선택</span>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-[1.35fr_0.85fr_0.9fr_0.9fr]">
            {RECOMMENDATION_FACILITY_GROUPS.map((group) => (
              <div key={group.group} className="rounded-sm border border-border bg-surface-alt p-4">
                <strong className="block text-[14px] font-bold text-text">{group.group}</strong>
                <div className="mt-3 flex flex-wrap gap-2">
                  {group.items.map((facility) => (
                    <button
                      key={facility.key}
                      type="button"
                      onClick={() => toggleFacility(facility.key)}
                      className={`h-10 whitespace-nowrap rounded-sm border px-4 text-[13px] font-semibold transition ${
                        facilities.has(facility.key)
                          ? 'border-primary bg-primary text-surface'
                          : 'border-border bg-surface text-text-muted hover:border-primary hover:text-primary'
                      }`}
                    >
                      {facility.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <footer className="flex items-center justify-between gap-4 rounded-sm border border-border bg-surface-alt px-5 py-4 text-[13px] font-semibold text-text-muted">
          <span>
            {selectedUniversity?.name || '대학 미선택'} · {formatDuration(maxCommuteMinutes)} 이내 · {priority === 'budget' ? '예산 우선' : '교통 우선'} · 시설 {facilities.size}개
          </span>
          <button type="submit" disabled={disabled} className="app-floating-button h-11 min-h-11 w-[220px] bg-primary text-surface hover:bg-primary-hover hover:text-surface disabled:cursor-wait disabled:opacity-60">
            {finding ? '동네 찾는 중' : saving ? '조건 저장 중' : '동네 찾기'}
          </button>
        </footer>
      </form>

      {finding ? <FindingDialog /> : null}
      {dialog ? <NoticeDialog title={dialog.title} message={dialog.message} onClose={() => setDialog(null)} /> : null}
    </main>
  );
}

function FindingDialog() {
  return (
    <div className="fixed inset-0 z-[1800] flex items-center justify-center bg-black/35 p-6" role="status" aria-live="polite">
      <div className="w-full max-w-[360px] rounded-sm border border-border bg-surface p-5 text-center text-text shadow-xl">
        <div className="mx-auto h-9 w-9 animate-spin rounded-full border-4 border-border border-t-primary" aria-hidden="true" />
        <h2 className="m-0 mt-4 text-[18px] font-bold">조건에 맞는 동네 찾는 중</h2>
        <p className="m-0 mt-2 text-[13px] leading-6 text-text-muted">최대 60초 정도 걸릴 수 있습니다.</p>
      </div>
    </div>
  );
}

function NoticeDialog({ title, message, onClose }: { title: string; message: string; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-[1800] flex items-center justify-center bg-black/35 p-6" role="alertdialog" aria-modal="true">
      <div className="w-full max-w-[420px] rounded-sm border border-border bg-surface p-5 text-text shadow-xl">
        <h2 className="m-0 text-[18px] font-bold">{title}</h2>
        <p className="m-0 mt-3 text-[14px] leading-6 text-text-muted">{message}</p>
        <button
          type="button"
          onClick={onClose}
          className="mt-5 h-10 w-full rounded-sm bg-primary text-[13px] font-bold text-surface transition hover:bg-primary-hover"
        >
          조건 다시 조정하기
        </button>
      </div>
    </div>
  );
}

function recommendationErrorMessage(error: unknown) {
  const response = (error as {
    response?: {
      status?: number;
      data?: { detail?: string; message?: string } | string;
    };
    code?: string;
    message?: string;
  })?.response;
  const status = response?.status;
  const data = response?.data;
  const detail = typeof data === 'string' ? data : data?.detail || data?.message;

  if (status === 403) {
    return `추천 요청 권한 확인에 실패했습니다. 다시 시도해 주세요.${detail ? ` (${detail})` : ''}`;
  }
  if (status === 400) {
    return `조건 형식을 확인하지 못했습니다.${detail ? ` (${detail})` : ''}`;
  }
  if ((error as { code?: string })?.code === 'ECONNABORTED') {
    return '추천 요청 시간이 초과되었습니다. 조건을 조금 줄이거나 잠시 후 다시 시도해 주세요.';
  }
  if (status) {
    return `추천 요청이 실패했습니다. 상태 코드 ${status}${detail ? `: ${detail}` : ''}`;
  }
  return '추천 요청이 완료되지 않았습니다. 잠시 후 다시 시도하거나 조건을 조금 줄여 주세요.';
}

function normalizeSchoolName(value: string) {
  return value.trim().replace(/\s+/g, ' ');
}

function ConditionCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="min-h-[198px] rounded-sm border border-border bg-surface p-5 shadow-floating">
      <h2 className="m-0 text-[18px] font-bold text-text">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function NumberField({
  label,
  unit,
  value,
  onChange,
  min,
  step = 1,
  disabled = false,
}: {
  label: string;
  unit: string;
  value: string;
  onChange: (value: string) => void;
  min: number;
  step?: number;
  disabled?: boolean;
}) {
  return (
    <label className="grid gap-2 text-[13px] font-semibold text-text">
      {label}
      <NumberInput unit={unit} value={value} onChange={onChange} min={min} step={step} disabled={disabled} />
    </label>
  );
}

function CommuteTimeField({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const totalMinutes = Math.max(0, Number(value) || 0);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  const update = (nextHours: number, nextMinutes: number) => {
    const safeHours = Math.max(0, Number.isFinite(nextHours) ? nextHours : 0);
    const safeMinutes = Math.min(59, Math.max(0, Number.isFinite(nextMinutes) ? nextMinutes : 0));
    onChange(String(safeHours * 60 + safeMinutes));
  };

  return (
    <fieldset className="grid gap-2">
      <legend className="text-[13px] font-semibold text-text">통학 허용 시간</legend>
      <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] items-center gap-2">
        <NumberInput unit="시간" value={String(hours)} onChange={(next) => update(Number(next), minutes)} min={0} step={1} />
        <NumberInput unit="분" value={String(minutes)} onChange={(next) => update(hours, Number(next))} min={0} step={10} />
        <span className="whitespace-nowrap text-[13px] font-semibold text-text-muted">이내</span>
      </div>
      <p className="m-0 text-[12px] font-semibold text-text-muted">{formatDuration(value)} 이내</p>
    </fieldset>
  );
}

function NumberInput({
  unit,
  value,
  onChange,
  min,
  step = 1,
  disabled = false,
  suffix,
}: {
  unit: string;
  value: string;
  onChange: (value: string) => void;
  min: number;
  step?: number;
  disabled?: boolean;
  suffix?: string;
}) {
  return (
    <span className="flex h-11 w-full items-center rounded-sm border border-border bg-surface-alt px-3 transition focus-within:border-primary">
      <input
        type="number"
        min={min}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="min-w-0 flex-1 border-0 bg-transparent text-[14px] outline-none disabled:text-text-subtle"
      />
      <span className="shrink-0 text-[13px] text-text-muted">{unit}{suffix ? ` ${suffix}` : ''}</span>
    </span>
  );
}

function formatPyeong(value: string) {
  const area = Number(value);
  if (!Number.isFinite(area) || area <= 0) return '';
  return `(${(area / 3.3058).toFixed(1)}평)`;
}

function formatDuration(value: string) {
  const totalMinutes = Math.max(0, Number(value) || 0);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours}시간 ${minutes}분`;
}

function PriorityToggle({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-10 rounded-sm px-3 text-center text-[13px] font-semibold transition ${
        active
          ? 'bg-surface text-primary shadow-sm'
          : 'text-text-muted hover:bg-surface/70 hover:text-text'
      }`}
    >
      {children}
    </button>
  );
}
