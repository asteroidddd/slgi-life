import { useEffect, useState } from 'react';

/* -------------------------------------------------------------------------- */
/* Gauge — SVG circular gauge primitive                                        */
/* -------------------------------------------------------------------------- */

export interface GaugeProps {
  /** Score value between 0 and 100. */
  value: number;
  /** Visual size variant. */
  size?: 'sm' | 'md';
  /** Optional label below the gauge. */
  label?: string;
  /** Whether to animate the arc fill on mount. Default true. */
  animate?: boolean;
  /** Additional CSS classes on the outer wrapper. */
  className?: string;
}

const SIZE_MAP = { sm: 80, md: 120 } as const;
const STROKE_WIDTH = { sm: 6, md: 8 } as const;

/**
 * Map a 0-100 value to a stroke color using the same thresholds as MetricBar.
 * Uses CSS custom properties so colors stay in sync with the design system.
 */
function scoreToStrokeColor(value: number): string {
  if (value < 25) return 'var(--color-danger)';
  if (value < 45) return 'var(--color-warning)';
  if (value < 65) return 'var(--color-success)';
  if (value < 85) return 'var(--color-info)';
  return 'var(--color-metric-5)';
}

export default function Gauge({
  value,
  size = 'md',
  label,
  animate = true,
  className = '',
}: GaugeProps) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const rounded = Math.round(clamped);

  const dim = SIZE_MAP[size];
  const sw = STROKE_WIDTH[size];
  const radius = (dim - sw) / 2;
  const circumference = 2 * Math.PI * radius;
  const targetOffset = circumference * (1 - clamped / 100);

  const [offset, setOffset] = useState(animate ? circumference : targetOffset);

  useEffect(() => {
    if (!animate) {
      setOffset(targetOffset);
      return;
    }
    const raf = requestAnimationFrame(() => {
      setOffset(targetOffset);
    });
    return () => cancelAnimationFrame(raf);
  }, [animate, targetOffset, circumference]);

  const strokeColor = scoreToStrokeColor(clamped);
  const textSize = size === 'sm' ? 'text-body-base' : 'text-feature-heading';

  return (
    <div
      className={`inline-flex flex-col items-center gap-1 ${className}`}
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={rounded}
      aria-label={label ?? `${rounded}점`}
    >
      {/* SVG + central text wrapper — needs relative positioning */}
      <div className="relative inline-flex items-center justify-center">
        <svg
          width={dim}
          height={dim}
          viewBox={`0 0 ${dim} ${dim}`}
          className="transform -rotate-90"
        >
          {/* Track circle */}
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            fill="none"
            stroke="var(--color-surface-alt)"
            strokeWidth={sw}
          />
          {/* Fill circle */}
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth={sw}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{
              transition: animate ? 'stroke-dashoffset 1.5s ease-out' : 'none',
            }}
          />
        </svg>
        {/* Central value */}
        <span
          className={`absolute ${textSize} font-semibold tabular text-text`}
        >
          {rounded}
        </span>
      </div>
      {label && (
        <span className="text-caption text-text-muted">{label}</span>
      )}
    </div>
  );
}
