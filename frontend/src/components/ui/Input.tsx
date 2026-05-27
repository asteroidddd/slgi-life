import { forwardRef, useId } from 'react';
import type { InputHTMLAttributes, ReactNode } from 'react';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  leftSlot?: ReactNode;
  rightSlot?: ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, leftSlot, rightSlot, id, className, disabled, ...rest },
  ref
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;

  const describedBy =
    [error ? errorId : null, hint && !error ? hintId : null].filter(Boolean).join(' ') ||
    undefined;

  return (
    <div
      className={`flex flex-col gap-2 w-full ${disabled ? 'opacity-60' : ''} ${className ?? ''}`}
    >
      {label && (
        <label htmlFor={inputId} className="text-caption font-normal text-text tracking-normal">
          {label}
        </label>
      )}
      <div
        className={`flex items-center h-10 bg-surface border rounded-sm px-3 gap-2 transition-all duration-[120ms] ease-out ${
          error
            ? 'border-danger focus-within:border-danger focus-within:border-2 focus-within:px-[11px]'
            : 'border-border focus-within:border-focus-ring focus-within:border-2 focus-within:px-[11px]'
        } ${disabled ? 'bg-surface-alt cursor-not-allowed' : ''}`}
      >
        {leftSlot && (
          <span className="inline-flex items-center justify-center text-text-muted shrink-0">
            {leftSlot}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`flex-1 border-none outline-none bg-transparent text-body-base text-text tracking-normal min-w-0 h-full placeholder:text-text-subtle ${
            disabled ? 'cursor-not-allowed' : ''
          }`}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          disabled={disabled}
          {...rest}
        />
        {rightSlot && (
          <span className="inline-flex items-center justify-center text-text-muted shrink-0">
            {rightSlot}
          </span>
        )}
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

export default Input;
