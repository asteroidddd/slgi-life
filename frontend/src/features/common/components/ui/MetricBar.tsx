type Tone = 'score' | 'weight';
type Unit = '%' | '/100';

export interface MetricBarProps {
  label: string;
  value: number;
  tone?: Tone;
  unit?: Unit;
  ariaLabel?: string;
}

function scoreToClass(value: number): string {
  if (value < 25) return 'bg-danger';
  if (value < 45) return 'bg-warning';
  if (value < 65) return 'bg-success';
  if (value < 85) return 'bg-metric-4';
  return 'bg-metric-5';
}

function MetricBar({
  label,
  value,
  tone = 'score',
  unit,
  ariaLabel,
}: MetricBarProps) {
  const clamped = Number.isFinite(value)
    ? Math.max(0, Math.min(100, value))
    : 0;
  const rounded = Math.round(clamped);
  const display = unit ? `${rounded}${unit}` : `${rounded}`;
  const fillClass = tone === 'score' ? scoreToClass(clamped) : 'bg-primary';
  const computedAria =
    ariaLabel ?? `${label} ${tone === 'weight' ? '가중치' : '점수'}`;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between text-caption tracking-normal">
        <span className="text-text">{label}</span>
        <span className="text-text font-medium tabular">{display}</span>
      </div>
      <div
        className="w-full h-4 bg-surface-alt rounded-full overflow-hidden relative"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={rounded}
        aria-label={computedAria}
      >
        <span
          className={`block h-full rounded-full transition-all duration-200 ease-out ${fillClass}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

export default MetricBar;
