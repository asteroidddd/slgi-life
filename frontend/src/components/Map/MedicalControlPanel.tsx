import { useState } from 'react';

type MedicalCategory = 'hospital' | 'dental' | 'pharmacy' | 'emergency';

const MEDICAL_LABELS: Record<MedicalCategory, string> = {
  hospital: '병원',
  dental: '치과',
  pharmacy: '약국',
  emergency: '응급실',
};

const MEDICAL_ICONS: Record<MedicalCategory, string> = {
  hospital: '🏥',
  dental: '🦷',
  pharmacy: '💊',
  emergency: '🚑',
};

const MEDICAL_ORDER: MedicalCategory[] = ['hospital', 'dental', 'pharmacy', 'emergency'];
const DEFAULT_SPECIALTY_GROUPS = [
  '일반',
  '내과',
  '외과',
  '이비인후과',
  '안과',
  '피부과',
  '비뇨기과',
  '가정의학과',
  '산부인과',
  '소아과',
  '정신과',
  '성형외과',
  '신경과',
  '신경외과',
  '재활',
  '기타',
  '한의원',
];

function specialtyLabel(selected: Set<string>): string {
  if (selected.size === 0) return '병원';
  const [first] = Array.from(selected);
  if (selected.size === 1) return first;
  return `${first} 외 ${selected.size - 1}`;
}

export type { MedicalCategory };

export default function MedicalControlPanel({
  categories,
  specialtyGroups,
  selectedSpecialtyGroups,
  openNow,
  onToggleCategory,
  onToggleSpecialtyGroup,
  onResetSpecialtyGroups,
  onToggleOpenNow,
  onReset,
}: {
  categories: Set<MedicalCategory>;
  specialtyGroups: string[];
  selectedSpecialtyGroups: Set<string>;
  openNow: boolean;
  onToggleCategory: (key: MedicalCategory) => void;
  onToggleSpecialtyGroup: (name: string) => void;
  onResetSpecialtyGroups: () => void;
  onToggleOpenNow: () => void;
  onReset: () => void;
}) {
  const [specialtyOpen, setSpecialtyOpen] = useState(false);
  const hospitalActive = categories.has('hospital');
  const specialtyOptions = [
    '전체',
    ...Array.from(new Set((specialtyGroups.length ? specialtyGroups : DEFAULT_SPECIALTY_GROUPS).filter(Boolean))),
  ];

  const resetSpecialties = () => {
    onResetSpecialtyGroups();
  };

  const toggleSpecialty = (name: string) => {
    if (name === '전체') {
      onResetSpecialtyGroups();
      return;
    }
    onToggleSpecialtyGroup(name);
  };

  return (
    <div className="pointer-events-auto relative z-[600] grid w-[152px] gap-1.5 rounded-card border border-border bg-surface/95 p-2 shadow-lg backdrop-blur">
      <button
        type="button"
        onClick={onToggleOpenNow}
        aria-pressed={openNow}
        className={`flex h-9 items-center justify-between rounded-[var(--map-control-radius)] border px-2.5 text-left text-[12px] font-semibold shadow-sm transition ${openNow ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'border-border bg-surface text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}
      >
        <span>지금 문 연 곳</span>
        <span className={`relative h-5 w-9 rounded-full transition ${openNow ? 'bg-[var(--color-heatmap-4)]' : 'bg-border'}`} aria-hidden="true">
          <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-surface shadow-sm transition ${openNow ? 'left-[18px]' : 'left-0.5'}`} />
        </span>
      </button>

      <div className="grid gap-1.5">
        {MEDICAL_ORDER.map((key) => {
          const active = categories.has(key);
          if (key !== 'hospital') {
            return (
              <button
                key={key}
                type="button"
                onClick={() => onToggleCategory(key)}
                className={`h-9 w-full rounded-[var(--map-control-radius)] border px-3 text-left text-[13px] font-semibold shadow-sm transition ${active ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'border-border bg-surface/95 text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}
              >
                <span className="inline-flex items-center gap-1.5">
                  <span aria-hidden="true" className="inline-flex h-4 w-4 items-center justify-center">{MEDICAL_ICONS[key]}</span>
                  <span>{MEDICAL_LABELS[key]}</span>
                </span>
              </button>
            );
          }

          return (
            <div key={key} className="relative">
              <div className={`flex h-9 w-full min-w-0 items-center overflow-hidden rounded-[var(--map-control-radius)] border px-3 shadow-sm transition ${hospitalActive ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'border-border bg-surface/95 text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}>
                <button
                  type="button"
                  onClick={() => {
                    if (specialtyOpen) {
                      setSpecialtyOpen(false);
                      return;
                    }
                    resetSpecialties();
                    onToggleCategory('hospital');
                  }}
                  className="flex min-w-0 flex-1 items-center gap-1.5 overflow-hidden text-left text-[13px] font-semibold"
                >
                  <span aria-hidden="true" className="inline-flex h-4 w-4 shrink-0 items-center justify-center">{MEDICAL_ICONS[key]}</span>
                  <span className="block min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap" title={specialtyLabel(selectedSpecialtyGroups)}>{specialtyLabel(selectedSpecialtyGroups)}</span>
                </button>
                <button
                  type="button"
                  aria-label="진료과목 선택"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    setSpecialtyOpen((value) => !value);
                  }}
                  className="ml-2 flex h-full shrink-0 items-center justify-center text-[14px] leading-none"
                >
                  <span aria-hidden="true" className={`transition ${specialtyOpen ? 'rotate-180' : ''}`}>▾</span>
                </button>
              </div>
              {specialtyOpen ? (
                <div className="absolute left-[calc(100%+8px)] top-0 z-[720] grid max-h-[calc(100vh-96px)] w-[196px] gap-1 overflow-y-auto rounded-card border border-border bg-surface/95 p-2 shadow-xl backdrop-blur">
                  <p className="m-0 rounded-[6px] bg-surface-alt px-2 py-1.5 text-[11px] font-semibold leading-4 text-text-muted">
                    HIRA 진료과목 및 전문의 수 자료 기준입니다. 실제 진료 가능 여부와 다를 수 있어 참고용입니다.
                  </p>
                  {specialtyOptions.map((name) => {
                    const selected = name === '전체' ? selectedSpecialtyGroups.size === 0 : selectedSpecialtyGroups.has(name);
                    return (
                      <button
                        key={name}
                        type="button"
                        onClick={() => toggleSpecialty(name)}
                        className={`flex h-7 items-center justify-between rounded-[var(--map-control-radius)] px-2 text-left text-[12px] font-semibold transition ${selected ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'text-text-muted hover:bg-surface-alt hover:text-text'}`}
                      >
                        <span className="truncate">{name}</span>
                        {selected ? <span className="ml-1 shrink-0 text-[12px]">✓</span> : null}
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      <button
        type="button"
        onClick={() => {
          setSpecialtyOpen(false);
          resetSpecialties();
          onReset();
        }}
        className="h-9 w-full rounded-[var(--map-control-radius)] border border-border bg-surface-alt px-3 text-[13px] font-semibold text-text-muted shadow-sm transition hover:bg-border/60 hover:text-text"
      >
        초기화
      </button>
    </div>
  );
}
