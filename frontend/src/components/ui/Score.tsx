import type { HTMLAttributes } from 'react';

export type ScoreSize = 'md' | 'lg';

export interface ScoreProps extends Omit<HTMLAttributes<HTMLDivElement>, 'children'> {
  value: number;
  unit?: string;
  delta?: number;
  size?: ScoreSize;
  tone?: 'danger' | 'warning' | 'success' | 'neutral';
  ariaLabel?: string;
}

function tonalCategoryFromValue(
  value: number
): 'danger' | 'warning' | 'success' | 'neutral' {
  if (value < 40) return 'danger';
  if (value < 70) return 'warning';
  return 'success';
}

const toneValueClasses: Record<string, string> = {
  neutral: 'text-text',
  success: 'text-success',
  warning: 'text-text-muted',
  danger: 'text-danger',
};

const sizeValueClasses: Record<ScoreSize, string> = {
  md: 'text-card-heading font-semibold leading-[1.2] tracking-[-0.28px]',
  lg: 'text-data-display font-semibold leading-none tracking-[-0.48px]',
};

function Score({
  value,
  unit,
  delta,
  size = 'md',
  tone,
  ariaLabel,
  className,
  ...rest
}: ScoreProps) {
  const tonalClass = tone ?? tonalCategoryFromValue(value);

  const deltaSign = delta != null ? (delta > 0 ? '\u25B2' : delta < 0 ? '\u25BC' : '') : '';
  const deltaTone =
    delta == null ? '' : delta > 0 ? 'text-success' : delta < 0 ? 'text-danger' : 'text-text-subtle';

  return (
    <div
      className={`inline-flex items-baseline gap-2 tracking-normal leading-none text-text ${className ?? ''}`}
      role="text"
      aria-label={ariaLabel ?? `${value}${unit ?? ''}`}
      {...rest}
    >
      <span className={`font-display tabular ${toneValueClasses[tonalClass]} ${sizeValueClasses[size]}`}>
        {value}
      </span>
      {unit && (
        <span className="font-base text-caption font-normal text-text-muted tracking-normal">
          {unit}
        </span>
      )}
      {delta != null && (
        <span className={`inline-flex items-center gap-0.5 font-mono text-mono-label font-normal tracking-[0.26px] text-text-subtle ml-1 ${deltaTone}`}>
          <span aria-hidden="true">{deltaSign}</span>
          <span className="tabular">{Math.abs(delta)}</span>
        </span>
      )}
    </div>
  );
}

export default Score;
