import { useEffect, useState } from 'react';

import { readLocalStorage, writeLocalStorage } from '@/features/common/lib/browserStorage';

const MODE_GUIDE_STORAGE_KEY = 'map.modeGuide.open';
const MODE_GUIDE_SYNC_EVENT = 'map-mode-guide-sync';

function readStoredGuideState() {
  const stored = readLocalStorage(MODE_GUIDE_STORAGE_KEY);
  if (stored === 'false') return false;
  if (stored === 'true') return true;
  return true;
}

function FilterButton({
  children,
  active,
  onClick,
  className = '',
}: {
  children: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex h-9 w-full items-center rounded-[var(--map-control-radius)] border px-3 text-left text-[13px] font-semibold leading-none shadow-sm transition ${
        active
          ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]'
          : 'border-border bg-surface/95 text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
      } ${className}`}
    >
      {children}
    </button>
  );
}



function ResetButton({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="h-9 w-full rounded-[var(--map-control-radius)] border border-border bg-surface-alt px-3 text-[13px] font-semibold text-text-muted shadow-sm transition hover:bg-border/60 hover:text-text"
    >
      {children}
    </button>
  );
}

function SegmentButton({
  children,
  active,
  onClick,
}: {
  children: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-8 rounded-[var(--map-control-radius)] px-3 text-[13px] font-semibold transition ${
        active ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm' : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
      }`}
    >
      {children}
    </button>
  );
}

function ModeGuide({
  title,
  children,
  className = '',
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(readStoredGuideState);

  useEffect(() => {
    function syncOpenState() {
      setOpen(readStoredGuideState());
    }

    syncOpenState();
    window.addEventListener('storage', syncOpenState);
    window.addEventListener(MODE_GUIDE_SYNC_EVENT, syncOpenState);
    return () => {
      window.removeEventListener('storage', syncOpenState);
      window.removeEventListener(MODE_GUIDE_SYNC_EVENT, syncOpenState);
    };
  }, []);

  function toggleOpen() {
    setOpen((value) => {
      const next = !value;
      writeLocalStorage(MODE_GUIDE_STORAGE_KEY, next ? 'true' : 'false');
      window.dispatchEvent(new Event(MODE_GUIDE_SYNC_EVENT));
      return next;
    });
  }

  return (
    <aside
      className={`pointer-events-auto relative z-0 rounded-card border border-border/70 bg-[var(--map-guide-bg)] text-left shadow-lg backdrop-blur-md transition-[width,padding] ${
        open ? 'w-[var(--map-control-width)] px-3 py-2.5' : 'w-auto min-w-[96px] px-2.5 py-2'
      } ${className}`}
      aria-label={`${title} 안내`}
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={toggleOpen}
        className="flex w-full items-center justify-between gap-3 bg-transparent p-0 text-left"
      >
        <strong className="block whitespace-nowrap text-[13px] font-semibold text-text">{title}</strong>
        <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border/80 bg-surface/70 text-[12px] font-bold leading-none text-text-muted">
          {open ? '-' : '+'}
        </span>
      </button>
      {open ? <p className="m-0 mt-1 whitespace-pre-line break-keep text-[12px] leading-[1.45] text-text-muted">{children}</p> : null}
    </aside>
  );
}

function IconTooltip({ children }: { children: React.ReactNode }) {
  return (
    <span className="app-tooltip app-tooltip--compact pointer-events-none absolute bottom-[calc(100%+8px)] left-1/2 z-[var(--tooltip-z)] hidden -translate-x-1/2 whitespace-nowrap group-hover:block group-focus-within:block">
      {children}
    </span>
  );
}

function DropdownButton({
  id,
  label,
  active,
  open,
  onToggle,
  onClose,
  children,
  width = 'w-[224px]',
  disabled = false,
}: {
  id: string;
  label: string;
  active?: boolean;
  open: boolean;
  onToggle: (id: string) => void;
  onClose?: () => void;
  children: React.ReactNode;
  width?: string;
  disabled?: boolean;
}) {
  return (
    <div className={`relative min-w-0 ${open ? 'z-[1300]' : 'z-[600]'} ${width}`}>
      <button
        type="button"
        onClick={() => { if (!disabled) onToggle(id); }}
        disabled={disabled}
        className={`flex h-9 w-full min-w-0 items-center justify-between overflow-hidden rounded-[var(--map-control-radius)] border px-3 text-[13px] font-semibold shadow-sm transition ${
          active ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'border-border bg-surface/95 text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
        } ${disabled ? 'cursor-not-allowed opacity-45 hover:bg-surface/95 hover:text-text' : ''}`}
        aria-expanded={open}
      >
        <span className="block min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-left" title={label}>{label}</span>
        <span className="ml-2 shrink-0 text-[14px] leading-none" aria-hidden="true">▾</span>
      </button>
      {open ? (
        <div className="absolute left-[calc(100%+8px)] top-0 z-[1400] w-[300px] rounded-[8px] border border-border bg-surface p-3 shadow-xl">
          {onClose ? (
            <button type="button" onClick={onClose} className="absolute right-2 top-2 h-7 w-7 rounded-[6px] bg-surface-alt text-[16px] text-text-muted">×</button>
          ) : null}
          {children}
        </div>
      ) : null}
    </div>
  );
}

function ChoiceList({
  items,
  selected,
  onSelect,
}: {
  items: Array<{ value: string; label: string }>;
  selected: string;
  onSelect: (value: string) => void;
}) {
  return (
    <div className="grid gap-1">
      {items.map((item) => (
        <button
          key={item.value}
          type="button"
          onClick={() => onSelect(item.value)}
          className={`h-8 rounded-[6px] px-2 text-left text-[13px] font-medium ${
            selected === item.value ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function RangePanel({
  title,
  unit,
  min,
  max,
  onChange,
  presets,
  step = 1,
}: {
  title: string;
  unit: string;
  min: number;
  max: number;
  onChange: (min: number, max: number) => void;
  presets: Array<{ label: string; min: number; max: number }>;
  step?: number;
}) {
  return (
    <div className="grid gap-3">
      <h3 className="m-0 text-[14px] font-semibold text-text">{title}</h3>
      <div className="flex items-end gap-2">
        <label className="min-w-0 flex-1 grid gap-1 text-[12px] font-semibold text-text-muted">
          최소 {unit}
          <input
            type="number"
            step={step}
            value={min}
            onChange={(e) => onChange(Number(e.target.value), max)}
            className="h-8 w-full min-w-0 rounded-[6px] border border-border bg-surface-alt px-2 text-[13px] text-text"
          />
        </label>
        <label className="min-w-0 flex-1 grid gap-1 text-[12px] font-semibold text-text-muted">
          최대 {unit}
          <input
            type="number"
            step={step}
            value={max}
            onChange={(e) => onChange(min, Number(e.target.value))}
            className="h-8 w-full min-w-0 rounded-[6px] border border-border bg-surface-alt px-2 text-[13px] text-text"
          />
        </label>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {presets.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => onChange(p.min, p.max)}
            className="h-8 rounded-[6px] bg-surface-alt px-2 text-[12px] font-semibold text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]"
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}



export {
  ChoiceList,
  DropdownButton,
  FilterButton,
  IconTooltip,
  ModeGuide,
  RangePanel,
  ResetButton,
  SegmentButton,
};
