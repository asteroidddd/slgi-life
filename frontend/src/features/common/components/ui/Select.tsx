import { forwardRef, useId } from 'react';
import type { ReactNode, SelectHTMLAttributes } from 'react';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  children: ReactNode;
}

const ChevronDown = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 14 14"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M3.5 5.25L7 8.75L10.5 5.25"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, hint, error, id, className, disabled, children, ...rest },
  ref
) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  const hintId = `${selectId}-hint`;
  const errorId = `${selectId}-error`;

  const describedBy =
    [error ? errorId : null, hint && !error ? hintId : null].filter(Boolean).join(' ') ||
    undefined;

  return (
    <div
      className={`flex flex-col gap-2 w-full ${className ?? ''}`}
    >
      {label && (
        <label htmlFor={selectId} className="text-caption font-normal text-text tracking-normal">
          {label}
        </label>
      )}
      <div
        className={`relative flex items-center h-10 bg-surface border rounded-sm transition-all duration-[120ms] ease-out ${
          error
            ? 'border-danger focus-within:border-danger focus-within:border-2'
            : 'border-border focus-within:border-focus-ring focus-within:border-2'
        } ${disabled ? 'bg-surface-alt opacity-60' : ''}`}
      >
        <select
          ref={ref}
          id={selectId}
          className={`appearance-none flex-1 border-none outline-none bg-transparent text-body-base text-text tracking-normal h-full px-3 pr-8 min-w-0 ${
            disabled ? 'cursor-not-allowed' : 'cursor-pointer'
          }`}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          disabled={disabled}
          {...rest}
        >
          {children}
        </select>
        <span className="absolute right-3 inline-flex items-center justify-center text-text-muted pointer-events-none" aria-hidden="true">
          <ChevronDown />
        </span>
      </div>
      {error ? (
        <span id={errorId} className="text-micro text-danger tracking-normal" role="alert">
          {error}
        </span>
      ) : (
        hint && (
          <span id={hintId} className="text-micro text-text-muted tracking-normal">
            {hint}
          </span>
        )
      )}
    </div>
  );
});

export default Select;
