import { forwardRef, useId } from 'react';
import type { ChangeEvent, InputHTMLAttributes, ReactNode } from 'react';

export interface SliderProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'type' | 'size'> {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: ReactNode;
  valueText?: ReactNode;
  hideHeader?: boolean;
}

const thumbClasses = [
  '[&::-webkit-slider-thumb]:appearance-none',
  '[&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5',
  '[&::-webkit-slider-thumb]:rounded-full',
  '[&::-webkit-slider-thumb]:bg-surface',
  '[&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-solid [&::-webkit-slider-thumb]:border-secondary',
  '[&::-webkit-slider-thumb]:-mt-[8px]',
  '[&::-webkit-slider-thumb]:cursor-pointer',
  '[&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:duration-[120ms] [&::-webkit-slider-thumb]:ease-out',
  'hover:[&::-webkit-slider-thumb]:scale-105',
  'focus-visible:[&::-webkit-slider-thumb]:[box-shadow:0_0_0_4px_var(--color-focus-ring)]',
  '[&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:h-5',
  '[&::-moz-range-thumb]:rounded-full',
  '[&::-moz-range-thumb]:bg-surface',
  '[&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-solid [&::-moz-range-thumb]:border-secondary',
  '[&::-moz-range-thumb]:cursor-pointer',
  '[&::-moz-range-thumb]:transition-transform [&::-moz-range-thumb]:duration-[120ms] [&::-moz-range-thumb]:ease-out',
  'hover:[&::-moz-range-thumb]:scale-105',
  'focus-visible:[&::-moz-range-thumb]:[box-shadow:0_0_0_4px_var(--color-focus-ring)]',
].join(' ');

const trackClasses = [
  '[&::-webkit-slider-runnable-track]:h-1 [&::-webkit-slider-runnable-track]:rounded-full',
  '[&::-moz-range-track]:h-1 [&::-moz-range-track]:bg-border [&::-moz-range-track]:rounded-full',
  '[&::-moz-range-progress]:h-1 [&::-moz-range-progress]:bg-secondary [&::-moz-range-progress]:rounded-full',
].join(' ');

const Slider = forwardRef<HTMLInputElement, SliderProps>(function Slider(
  {
    value,
    onChange,
    min = 0,
    max = 100,
    step = 1,
    label,
    valueText,
    hideHeader = false,
    disabled,
    id,
    className,
    ...rest
  },
  ref
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const percent = ((value - min) / (max - min)) * 100;

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    onChange(Number(e.target.value));
  };

  return (
    <div className={`flex flex-col gap-2 w-full ${disabled ? 'opacity-50' : ''} ${className ?? ''}`}>
      {!hideHeader && (label || valueText) && (
        <div className="flex items-baseline justify-between gap-3">
          {label && (
            <label htmlFor={inputId} className="text-caption font-normal text-text tracking-normal">
              {label}
            </label>
          )}
          {valueText != null && (
            <span className="font-mono text-mono-label tracking-[0.26px] text-secondary font-normal uppercase tabular">
              {valueText}
            </span>
          )}
        </div>
      )}
      <input
        ref={ref}
        id={inputId}
        type="range"
        className={`ui-slider-track appearance-none w-full h-6 bg-transparent m-0 cursor-pointer disabled:cursor-not-allowed focus:outline-none ${trackClasses} ${thumbClasses}`}
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={handleChange}
        aria-valuetext={typeof valueText === 'string' ? valueText : undefined}
        style={{
          ['--ui-slider-fill' as string]: `${percent}%`,
        }}
        {...rest}
      />
    </div>
  );
});

export default Slider;
